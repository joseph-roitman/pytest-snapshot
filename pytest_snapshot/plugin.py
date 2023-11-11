import operator
import os
import re
from pathlib import Path
from typing import Any, AnyStr, Callable, Iterator, List, Optional, Tuple, Union

import pytest

try:
    from pytest import Parser as _Parser
except ImportError:
    from _pytest.config.argparsing import Parser as _Parser

try:
    from pytest import FixtureRequest as _FixtureRequest
except ImportError:
    from _pytest.fixtures import FixtureRequest as _FixtureRequest

from pytest_snapshot._utils import shorten_path, get_valid_filename, _pytest_expected_on_right
from pytest_snapshot._utils import flatten_filesystem_dict, _RecursiveDict

PARAMETRIZED_TEST_REGEX = re.compile(r'^.*?\[(.*)]$')


def pytest_addoption(parser: _Parser) -> None:
    group = parser.getgroup('snapshot')
    group.addoption(
        '--snapshot-update',
        action='store_true',
        help='Update snapshot files instead of testing against them.',
    )
    group.addoption(
        '--allow-snapshot-deletion',
        action='store_true',
        help='Allow snapshot deletion when updating snapshots.',
    )


@pytest.fixture
def snapshot(request: _FixtureRequest) -> Iterator["Snapshot"]:
    # FIXME Properly handle different node type
    assert isinstance(request.node, pytest.Function)
    default_snapshot_dir = _get_default_snapshot_dir(request.node)

    with Snapshot(request.config.option.snapshot_update,
                  request.config.option.allow_snapshot_deletion,
                  default_snapshot_dir) as snapshot:
        yield snapshot


def _assert_equal(value: AnyStr, snapshot: AnyStr) -> None:
    if _pytest_expected_on_right():
        assert value == snapshot
    else:
        assert snapshot == value


def _file_encode(string: str) -> bytes:
    """
    Returns the bytes that would be in a file created using ``path.write_text(string)``.
    See universal newlines documentation.
    """
    if '\r' in string:
        raise ValueError('''\
Snapshot testing strings containing "\\r" is not supported.
To snapshot test non-standard newlines you should convert the tested value to bytes.
Warning: git may decide to modify the newlines in the snapshot file.
To avoid this read \
https://docs.github.com/en/get-started/getting-started-with-git/configuring-git-to-handle-line-endings''')

    return string.replace('\n', os.linesep).encode()


def _file_decode(data: bytes) -> str:
    """
    Returns the string that would be read from a file using ``path.read_text(string)``.
    See universal newlines documentation.
    """
    return data.decode().replace('\r\n', '\n').replace('\r', '\n')


class Snapshot:
    _snapshot_update: bool
    _allow_snapshot_deletion: bool
    _created_snapshots: List[Path]
    _updated_snapshots: List[Path]
    _snapshots_to_delete: List[Path]
    _snapshot_dir: Path

    def __init__(self, snapshot_update: bool, allow_snapshot_deletion: bool, snapshot_dir: Path):
        self._snapshot_update = snapshot_update
        self._allow_snapshot_deletion = allow_snapshot_deletion
        self.snapshot_dir = snapshot_dir
        self._created_snapshots = []
        self._updated_snapshots = []
        self._snapshots_to_delete = []

    def __enter__(self) -> "Snapshot":
        return self

    def __exit__(self, *_: Any) -> None:
        if self._created_snapshots or self._updated_snapshots or self._snapshots_to_delete:
            message_lines = ['Snapshot directory was modified: {}'.format(shorten_path(self.snapshot_dir)),
                             '  (verify that the changes are expected before committing them to version control)']
            if self._created_snapshots:
                message_lines.append('  Created snapshots:')
                message_lines.extend('    ' + str(s.relative_to(self.snapshot_dir)) for s in self._created_snapshots)

            if self._updated_snapshots:
                message_lines.append('  Updated snapshots:')
                message_lines.extend('    ' + str(s.relative_to(self.snapshot_dir)) for s in self._updated_snapshots)

            if self._snapshots_to_delete:
                if self._allow_snapshot_deletion:
                    for path in self._snapshots_to_delete:
                        path.unlink()
                    message_lines.append('  Deleted snapshots:')
                else:
                    message_lines.append('  Snapshots that should be deleted: '
                                         '(run pytest with --allow-snapshot-deletion to delete them)')

                message_lines.extend('    ' + str(s.relative_to(self.snapshot_dir)) for s in self._snapshots_to_delete)

            pytest.fail('\n'.join(message_lines), pytrace=False)

    @property
    def snapshot_dir(self) -> Path:
        return self._snapshot_dir

    @snapshot_dir.setter
    def snapshot_dir(self, value: Union[str, 'os.PathLike[str]']) -> None:
        self._snapshot_dir = Path(value).absolute()

    def _snapshot_path(self, snapshot_name: Union[str, 'os.PathLike[str]']) -> Path:
        """
        Returns the absolute path to the given snapshot.
        """
        if isinstance(snapshot_name, Path):
            snapshot_path = snapshot_name.absolute()
        else:
            snapshot_path = self.snapshot_dir.joinpath(snapshot_name)

        # TODO: snapshot_path = snapshot_path.resolve(strict=False). Requires Python >3.6 for strict=False.
        if self.snapshot_dir not in snapshot_path.parents:
            raise ValueError('Snapshot path {} is not in {}'.format(
                shorten_path(snapshot_path), shorten_path(self.snapshot_dir)))

        return snapshot_path

    def _get_compare_encode_decode(self, value: AnyStr) -> Tuple[
        Callable[[AnyStr, AnyStr], None],
        Callable[[AnyStr], bytes],
        Callable[[bytes], AnyStr]
    ]:
        """
        Returns a 3-tuple of a compare function, an encoding function, and a decoding function.

        * The compare function should compare the object to the value of its snapshot,
          raising an AssertionError with a useful error message if they are different.
        * The encoding function should encode the value into bytes for saving to a snapshot file.
        * The decoding function should decode bytes from a snapshot file into a object.
        """
        if isinstance(value, str):
            return _assert_equal, _file_encode, _file_decode
        elif isinstance(value, bytes):
            noop: Callable[[bytes], bytes] = lambda x: x
            return _assert_equal, noop, noop
        else:
            raise TypeError('value must be str or bytes')

    def assert_match(self, value: AnyStr, snapshot_name: Union[str, 'os.PathLike[str]']) -> None:
        """
        Asserts that ``value`` equals the current value of the snapshot with the given ``snapshot_name``.

        If pytest was run with the --snapshot-update flag, the snapshot will instead be updated to ``value``.
        The test will fail if there were any changes to the snapshot.
        """
        __tracebackhide__ = operator.methodcaller("errisinstance", AssertionError)
        compare, encode, decode = self._get_compare_encode_decode(value)
        snapshot_path = self._snapshot_path(snapshot_name)

        if snapshot_path.is_file():
            encoded_expected_value = snapshot_path.read_bytes()
        elif snapshot_path.exists():
            raise AssertionError('snapshot exists but is not a file: {}'.format(shorten_path(snapshot_path)))
        else:
            encoded_expected_value = None

        if self._snapshot_update:
            encoded_value = encode(value)
            if encoded_expected_value is None or encoded_value != encoded_expected_value:
                decoded_encoded_value = decode(encoded_value)
                if decoded_encoded_value != value:
                    raise ValueError("value is not supported by pytest-snapshot's serializer.")

                snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                snapshot_path.write_bytes(encoded_value)
                if encoded_expected_value is None:
                    self._created_snapshots.append(snapshot_path)
                else:
                    self._updated_snapshots.append(snapshot_path)
        else:
            if encoded_expected_value is not None:
                expected_value = decode(encoded_expected_value)
                snapshot_diff_msg: Optional[str]
                try:
                    compare(value, expected_value)
                except AssertionError as e:
                    snapshot_diff_msg = str(e)
                else:
                    snapshot_diff_msg = None

                if snapshot_diff_msg is not None:
                    snapshot_diff_msg = 'value does not match the expected value in snapshot {}\n' \
                                        '  (run pytest with --snapshot-update to update snapshots)\n{}'.format(
                                            shorten_path(snapshot_path), snapshot_diff_msg)
                    raise AssertionError(snapshot_diff_msg)
            else:
                raise AssertionError(
                    "snapshot {} doesn't exist. (run pytest with --snapshot-update to create it)".format(
                        shorten_path(snapshot_path)))

    def assert_match_dir(
        self,
        dir_dict: _RecursiveDict[str, Union[bytes, str]],
        snapshot_dir_name: Union[str, 'os.PathLike[str]']
    ) -> None:
        """
        Asserts that the values in dir_dict equal the current values in the given snapshot directory.

        If pytest was run with the --snapshot-update flag, the snapshots will be updated.
        The test will fail if there were any changes to the snapshots.
        """
        __tracebackhide__ = operator.methodcaller("errisinstance", AssertionError)
        if not isinstance(dir_dict, dict):
            raise TypeError('dir_dict must be a dictionary')

        snapshot_dir_path = self._snapshot_path(snapshot_dir_name)
        values_by_filename = flatten_filesystem_dict(dir_dict)  # type: ignore[misc]
        if snapshot_dir_path.is_dir():
            existing_names = {p.relative_to(snapshot_dir_path).as_posix()
                              for p in snapshot_dir_path.rglob('*') if p.is_file()}
        elif snapshot_dir_path.exists():
            raise AssertionError('snapshot exists but is not a directory: {}'.format(shorten_path(snapshot_dir_path)))
        else:
            existing_names = set()

        names = set(values_by_filename)
        added_names = names - existing_names
        removed_names = existing_names - names
        if self._snapshot_update:
            self._snapshots_to_delete.extend(snapshot_dir_path.joinpath(name) for name in sorted(removed_names))
        else:
            if added_names or removed_names:
                message_lines = ['Values do not match snapshots in {}'.format(shorten_path(snapshot_dir_path)),
                                 '  (run pytest with --snapshot-update to update the snapshot directory)']
                if added_names:
                    message_lines.append("  Values without snapshots:")
                    message_lines.extend('    ' + s for s in added_names)
                if removed_names:
                    message_lines.append("  Snapshots without values:")
                    message_lines.extend('    ' + s for s in removed_names)
                raise AssertionError('\n'.join(message_lines))

        # Call assert_match to add, update, or assert equality for all snapshot files in the directory.
        for name, value in values_by_filename.items():
            self.assert_match(value, snapshot_dir_path.joinpath(name))  # pyright: ignore


def _get_default_snapshot_dir(node: pytest.Function) -> Path:
    """
    Returns the default snapshot directory for the pytest test.
    """
    test_module_dir = node.fspath.dirpath()
    test_module = node.fspath.purebasename
    if '[' not in node.name:
        test_name = node.name
        parametrize_name = None
    else:
        test_name = node.originalname
        parametrize_match = PARAMETRIZED_TEST_REGEX.match(node.name)
        assert parametrize_match is not None, 'Expected request.node.name to be of format TEST_FUNCTION[PARAMS]'
        parametrize_name = parametrize_match.group(1)
        parametrize_name = get_valid_filename(parametrize_name)
    default_snapshot_dir = test_module_dir.join('snapshots', test_module, test_name)
    if parametrize_name is not None:
        default_snapshot_dir = default_snapshot_dir.join(parametrize_name)
    return Path(str(default_snapshot_dir))

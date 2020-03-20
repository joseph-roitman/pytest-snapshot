# -*- coding: utf-8 -*-

import pytest
from packaging import version
from typing import Optional, List

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path


def pytest_addoption(parser):
    group = parser.getgroup('snapshot')
    group.addoption(
        '--snapshot-update',
        action='store_true',
        help='Update snapshots.'
    )


@pytest.fixture
def snapshot(request):
    with Snapshot(request.config.option.snapshot_update) as snapshot:
        yield snapshot


class Snapshot(object):
    _created_snapshots = None  # type: List[str]
    _updated_snapshots = None  # type: List[str]
    _snapshot_update = None  # type: bool
    _snapshot_dir = None  # type: Optional[Path]

    def __init__(self, snapshot_update):
        self._created_snapshots = []
        self._updated_snapshots = []
        self._snapshot_update = snapshot_update

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            return False
        if self._created_snapshots or self._updated_snapshots:
            message_lines = []
            if self._created_snapshots:
                message_lines.append("The following snapshots were created in '{}':".format(self._snapshot_dir))
                message_lines.extend('  ' + s for s in self._created_snapshots)

            if self._updated_snapshots:
                message_lines.append("The following snapshots were updated in '{}':".format(self._snapshot_dir))
                message_lines.extend('  ' + s for s in self._updated_snapshots)
            raise AssertionError('\n'.join(message_lines))

    @property
    def snapshot_dir(self):
        if self._snapshot_dir is None:
            raise AssertionError('snapshot.snapshot_dir was not set.')
        return self._snapshot_dir

    @snapshot_dir.setter
    def snapshot_dir(self, value):
        self._snapshot_dir = Path(value)

    def _snapshot_path(self, snapshot_name):
        return self._snapshot_dir.joinpath(snapshot_name)

    def assert_match(self, value, snapshot_name):
        """
        Asserts that ``value`` equals the current value of the snapshot with the given ``snapshot_name``.

        If pytest was run with the --snapshot-update flag, the snapshot will instead be updated to ``value``.
        The test will fail if the value changed.

        :type value: str
        :type snapshot_name: str
        """
        snapshot_path = self._snapshot_path(snapshot_name)

        if snapshot_path.is_file():
            expected_value = snapshot_path.read_text()
        elif snapshot_path.exists():
            raise AssertionError('invalid snapshot file {}'.format(snapshot_path))
        else:
            expected_value = None

        if self._snapshot_update:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            if expected_value is not None:
                if expected_value != value:
                    snapshot_path.write_text(value)
                    self._updated_snapshots.append(snapshot_name)
            else:
                snapshot_path.write_text(value)
                self._created_snapshots.append(snapshot_name)
        else:
            if expected_value is not None:
                # pytest diffs before version 5.4.0 required expected to be on the left hand side.
                expected_on_right = version.parse(pytest.__version__) >= version.parse("5.4.0")
                try:
                    if expected_on_right:
                        assert value == expected_value
                    else:
                        assert expected_value == value
                except AssertionError as e:
                    snapshot_diff_msg = str(e)
                else:
                    snapshot_diff_msg = None

                if snapshot_diff_msg:
                    snapshot_diff_msg = 'value does not match the expected value in snapshot {}\n{}'.format(
                        snapshot_path, snapshot_diff_msg)
                    raise AssertionError(snapshot_diff_msg)
            else:
                raise AssertionError(
                    "Snapshot '{}' doesn't exist in '{}'.\nRun pytest with --snapshot-update to create it.".format(
                        snapshot_name, self.snapshot_dir))

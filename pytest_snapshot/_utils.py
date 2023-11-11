import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, TypeVar, Union, cast

import pytest

SIMPLE_VERSION_REGEX = re.compile(r'([0-9]+)\.([0-9]+)\.([0-9]+)')
ILLEGAL_FILENAME_CHARS = r'\/:*?"<>|'

_K = TypeVar("_K")
_V = TypeVar("_V")
_RecursiveDict = Dict[_K, Union["_RecursiveDict", _V]]


def shorten_path(path: Path) -> Path:
    """
    Returns the path relative to the current working directory if possible. Otherwise return the path unchanged.
    """
    try:
        return path.relative_to(os.getcwd())
    except ValueError:
        return path


def get_valid_filename(s: str) -> str:
    """
    Return the given string converted to a string that can be used for a clean filename.
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    """
    s = str(s).strip().replace(' ', '_')
    s = re.sub(r'(?u)[^-\w.]', '', s)
    s = {'': 'empty', '.': 'dot', '..': 'dotdot'}.get(s, s)
    return s


def might_be_valid_filename(s: str) -> bool:
    """
    Returns false if the given string is definitely a path traversal or not a valid filename.
    Returns true if the string might be a valid filename.

    Note: This isn't secure, it just catches most accidental path traversals or invalid filenames.
    """
    return not (
        len(s) == 0
        or s == '.'
        or s == '..'
        or any(c in s for c in ILLEGAL_FILENAME_CHARS)
    )


def simple_version_parse(version: str) -> Tuple[int, ...]:
    """
    Returns a 3 tuple of the versions major, minor, and patch.
    Raises a value error if the version string is unsupported.
    """
    match = SIMPLE_VERSION_REGEX.match(version)
    if match is None:
        raise ValueError('Unsupported version format')

    return tuple(int(part) for part in match.groups())


def _pytest_expected_on_right() -> bool:
    """
    Returns true if pytest prints string diffs correctly for:

        assert tested_value == expected_value

    Returns false if pytest prints string diffs correctly for:

        assert expected_value == tested_value
    """
    # pytest diffs before version 5.4.0 assumed expected to be on the left hand side.
    try:
        pytest_version = simple_version_parse(pytest.__version__)
    except ValueError:
        return True
    else:
        return pytest_version >= (5, 4, 0)


def flatten_dict(d: _RecursiveDict[_K, _V]) -> List[Tuple[List[_K], _V]]:
    """
    Returns the flattened dict representation of the given dict.

    Example:

        >>> flatten_dict({
        ...     'a': 1,
        ...     'b': {
        ...         'c': 2
        ...     },
        ...     'd': {},
        ... })
        [(['a'], 1), (['b', 'c'], 2)]
    """
    assert type(d) is dict
    result: List[Tuple[List[_K], _V]] = []
    _flatten_dict(d, result, [])  # type: ignore[misc]
    return result


def _flatten_dict(
    obj: _RecursiveDict[_K, _V], result: List[Tuple[List[_K], _V]], prefix: List[_K]
) -> None:
    for k, v in obj.items():
        prefix.append(k)
        if type(v) is dict:
            _flatten_dict(cast(_RecursiveDict[_K, _V], v), result, prefix)
        else:
            result.append((list(prefix), cast(_V, v)))
        prefix.pop()


def flatten_filesystem_dict(d: _RecursiveDict[str, _V]) -> Dict[str, _V]:
    """
    Returns the flattened dict of a nested dictionary structure describing a filesystem.

    Raises ``ValueError`` if any of the dictionary keys are invalid filenames.

    Example:

        >>> flatten_filesystem_dict({
        ...     'file1.txt': '111',
        ...     'dir1': {
        ...         'file2.txt': '222'
        ...     },
        ... })
        {'file1.txt': '111', 'dir1/file2.txt': '222'}
    """
    result = {}
    for key_list, obj in flatten_dict(d):
        for i, key in enumerate(key_list):
            if not might_be_valid_filename(key):
                key_list_str = ''.join('[{!r}]'.format(k) for k in key_list[:i])
                raise ValueError('Key {!r} in d{} must be a valid file name.'.format(key, key_list_str))
        result['/'.join(key_list)] = obj

    return result

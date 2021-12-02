from unittest import mock

import pytest

from pytest_snapshot._utils import shorten_path, might_be_valid_filename, simple_version_parse, \
    _pytest_expected_on_right, flatten_dict, flatten_filesystem_dict
from tests.utils import assert_pytest_passes

from pathlib import Path


def test_help_message(testdir):
    result = testdir.runpytest('--help')
    result.stdout.fnmatch_lines([
        'snapshot:',
        '*--snapshot-update*Update snapshots.',
    ])


def test_default_snapshot_dir_without_parametrize(testdir):
    testdir.makepyfile("""
        from pathlib import Path

        def test_sth(snapshot):
            assert snapshot.snapshot_dir == \
                Path('snapshots/test_default_snapshot_dir_without_parametrize/test_sth').absolute()
    """)
    assert_pytest_passes(testdir)


def test_default_snapshot_dir_with_parametrize(testdir):
    testdir.makepyfile("""
        import pytest
        from pathlib import Path

        @pytest.mark.parametrize('param', ['a', 'b'])
        def test_sth(snapshot, param):
            assert snapshot.snapshot_dir == \
                Path('snapshots/test_default_snapshot_dir_with_parametrize/test_sth/{}'.format(param)).absolute()
    """)
    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sth?a? PASSED*',
        '*::test_sth?b? PASSED*',
    ])
    assert result.ret == 0


def test_shorten_path_in_cwd():
    assert shorten_path(Path('a/b').absolute()) == Path('a/b')


def test_shorten_path_outside_cwd():
    path_outside_cwd = Path().absolute().parent.joinpath('a/b')
    assert shorten_path(path_outside_cwd) == path_outside_cwd


@pytest.mark.parametrize('s, expected', [
    ('snapshot.txt', True),
    ('snapshot', True),
    ('.snapshot', True),
    ('snapshot.', True),
    ('', False),
    ('.', False),
    ('..', False),
    ('/', False),
    ('\\', False),
    ('a/b', False),
    ('a\\b', False),
    ('a:b', False),
    ('a"b', False),
])
def test_might_be_valid_filename(s, expected):
    assert might_be_valid_filename(s) == expected


@pytest.mark.parametrize('version_str, version', [
    ('0.0.0', (0, 0, 0)),
    ('55.2312.123132', (55, 2312, 123132)),
    ('1.2.3rc', (1, 2, 3)),
])
def test_simple_version_parse_success(version_str, version):
    assert simple_version_parse(version_str) == version


@pytest.mark.parametrize('version_str', [
    '',
    'rc1.2.3',
    '1!2.3.4',
    'a.b.c',
    '1.2',
    '1.2.',
])
def test_simple_version_parse_error(version_str):
    with pytest.raises(ValueError):
        simple_version_parse(version_str)


@pytest.mark.parametrize('version_str, expected_on_right', [
    ('4.9.9', False),
    ('5.3.9', False),
    ('5.4.0', True),
    ('5.4.1', True),
    ('5.5.0', True),
    ('6.0.0', True),
    ('badversion', True),
])
def test_pytest_expected_on_right(version_str, expected_on_right):
    with mock.patch('pytest.__version__', version_str):
        assert _pytest_expected_on_right() == expected_on_right


def test_flatten_dict():
    result = flatten_dict({
        'a': 1,
        'b': {
            'ba': 2,
            'bb': {
                'bba': 3,
                'bbb': 4,
            },
        },
        'empty': {},
    })
    result = sorted(result)  # Needed to support python 3.5
    assert result == [(['a'], 1), (['b', 'ba'], 2), (['b', 'bb', 'bba'], 3), (['b', 'bb', 'bbb'], 4)]


def test_flatten_filesystem_dict_success():
    result = flatten_filesystem_dict({
        'file1': 'file1_contents',
        'dir1': {
            'file2': 'file2_contents',
            'dir2': {
                'file3': 'file3_contents',
            },
        },
        'empty_dir': {},
    })
    assert result == {
        'file1': 'file1_contents',
        'dir1/file2': 'file2_contents',
        'dir1/dir2/file3': 'file3_contents',
    }


@pytest.mark.parametrize('illegal_filename', [
    'a/b',
    '.',
    '',
])
def test_flatten_filesystem_dict_illegal_filename(illegal_filename):
    with pytest.raises(ValueError):
        flatten_filesystem_dict({
            illegal_filename: 'contents'
        })

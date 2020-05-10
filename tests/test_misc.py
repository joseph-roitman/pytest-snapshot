from pytest_snapshot.plugin import shorten_path
from tests.utils import assert_pytest_passes

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path


def test_help_message(testdir):
    result = testdir.runpytest('--help')
    result.stdout.fnmatch_lines([
        'snapshot:',
        '*--snapshot-update*Update snapshots.',
    ])


def test_default_snapshot_dir_without_parametrize(testdir):
    testdir.makepyfile("""
        try:
            from pathlib import Path
        except ImportError:
            from pathlib2 import Path

        def test_sth(snapshot):
            assert snapshot.snapshot_dir == \
                Path('snapshots/test_default_snapshot_dir_without_parametrize/test_sth').absolute()
    """)
    assert_pytest_passes(testdir)


def test_default_snapshot_dir_with_parametrize(testdir):
    testdir.makepyfile("""
        import pytest
        try:
            from pathlib import Path
        except ImportError:
            from pathlib2 import Path

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

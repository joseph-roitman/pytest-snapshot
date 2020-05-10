import pytest

from pytest_snapshot.plugin import text_type
from tests.utils import assert_pytest_passes


@pytest.fixture
def basic_case_dir(testdir):
    case_dir = testdir.mkdir('case_dir')
    case_dir.join('snapshot1.txt').write_text(u'the value of snapshot1.txt', 'ascii')
    return case_dir


def test_assert_match_with_external_snapshot_path(testdir, basic_case_dir):
    testdir.makepyfile("""
        try:
            from pathlib import Path
        except ImportError:
            from pathlib2 import Path

        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match(u'the value of snapshot1.txt', Path('not_case_dir/snapshot1.txt').absolute())
    """)
    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        "E* AssertionError: Snapshot path not_case_dir?snapshot1.txt is not in case_dir",
    ])
    assert result.ret == 1


def test_assert_match_success(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match(u'the value of snapshot1.txt', 'snapshot1.txt')
    """)
    assert_pytest_passes(testdir)


def test_assert_match_failure(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match(u'the INCORRECT value of snapshot1.txt', 'snapshot1.txt')
    """)
    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        ">* raise AssertionError(snapshot_diff_msg)",
        'E* AssertionError: value does not match the expected value in snapshot case_dir?snapshot1.txt',
        "E* assert * == *",
        "E* - the value of snapshot1.txt",
        "E* + the INCORRECT value of snapshot1.txt",
        "E* ?    ++++++++++",
    ])
    assert result.ret == 1


def test_assert_match_invalid_type(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match(b'incorrect typed obj', 'snapshot1.txt')
    """)
    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        'E* TypeError: value must be {}'.format(text_type.__name__),
    ])
    assert result.ret == 1


def test_assert_match_missing_snapshot(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match(u'something', 'snapshot_that_doesnt_exist.txt')
    """)
    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        "E* snapshot case_dir?snapshot_that_doesnt_exist.txt doesn't exist. "
        "(run pytest with --snapshot-update to create it)",
    ])
    assert result.ret == 1


def test_assert_match_update_existing_snapshot_no_change(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match(u'the value of snapshot1.txt', 'snapshot1.txt')
    """)
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth PASSED*',
    ])
    assert result.ret == 0

    assert_pytest_passes(testdir)  # assert that snapshot update worked


@pytest.mark.parametrize('case_dir_repr',
                         ["'case_dir'",
                          "str(Path('case_dir').absolute())",
                          "Path('case_dir')",
                          "Path('case_dir').absolute()"],
                         ids=['relative_string_case_dir',
                              'abs_string_case_dir',
                              'relative_path_case_dir',
                              'abs_path_case_dir'])
@pytest.mark.parametrize('snapshot_name_repr',
                         ["'snapshot1.txt'",
                          "str(Path('case_dir/snapshot1.txt').absolute())",
                          "Path('case_dir/snapshot1.txt')",  # TODO: support this or "Path('snapshot1.txt')"?
                          "Path('case_dir/snapshot1.txt').absolute()"],
                         ids=['relative_string_snapshot_name',
                              'abs_string_snapshot_name',
                              'relative_path_snapshot_name',
                              'abs_path_snapshot_name'])
def test_assert_match_update_existing_snapshot(testdir, basic_case_dir, case_dir_repr, snapshot_name_repr):
    """
    Tests that `Snapshot.assert_match` works when updating an existing snapshot.

    Also tests that `Snapshot` supports absolute/relative str/Path snapshot directories and snapshot paths.
    """
    testdir.makepyfile("""
        try:
            from pathlib import Path
        except ImportError:
            from pathlib2 import Path

        def test_sth(snapshot):
            snapshot.snapshot_dir = {case_dir_repr}
            snapshot.assert_match(u'the NEW value of snapshot1.txt', {snapshot_name_repr})
    """.format(case_dir_repr=case_dir_repr, snapshot_name_repr=snapshot_name_repr))
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth PASSED*',
        '*::test_sth ERROR*',
        "E* AssertionError: Snapshot directory was modified: case_dir",
        'E*   Updated snapshots:',
        'E*     snapshot1.txt',
    ])
    assert result.ret == 1

    assert_pytest_passes(testdir)  # assert that snapshot update worked


def test_assert_match_update_existing_snapshot_and_exception_in_test(testdir, basic_case_dir):
    """
    Tests that `Snapshot.assert_match` works when updating an existing snapshot and then the test function fails.
    In this case, both the snapshot update error and the test function error are printed out.
    """
    testdir.makepyfile("""
        try:
            from pathlib import Path
        except ImportError:
            from pathlib2 import Path

        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match(u'the NEW value of snapshot1.txt', 'snapshot1.txt')
            assert False
    """)
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        '*::test_sth ERROR*',
        "E* AssertionError: Snapshot directory was modified: case_dir",
        'E*   Updated snapshots:',
        'E*     snapshot1.txt',
        'E* assert False',
    ])
    assert result.ret == 1


def test_assert_match_create_new_snapshot(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match(u'the NEW value of new_snapshot1.txt', 'sub_dir/new_snapshot1.txt')
    """)
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth PASSED*',
        '*::test_sth ERROR*',
        "E* Snapshot directory was modified: case_dir",
        'E*   Created snapshots:',
        'E*     sub_dir?new_snapshot1.txt',
    ])
    assert result.ret == 1

    assert_pytest_passes(testdir)  # assert that snapshot update worked


def test_assert_match_create_new_snapshot_in_default_dir(testdir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.assert_match(u'the value of new_snapshot1.txt', 'sub_dir/new_snapshot1.txt')
    """)
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth PASSED*',
        '*::test_sth ERROR*',
        "E* Snapshot directory was modified: snapshots?test_assert_match_create_new_snapshot_in_default_dir?test_sth",
        'E*   Created snapshots:',
        'E*     sub_dir?new_snapshot1.txt',
    ])
    assert result.ret == 1
    assert testdir.tmpdir.join(
        'snapshots/test_assert_match_create_new_snapshot_in_default_dir/test_sth/sub_dir/new_snapshot1.txt'
    ).read_text('utf-8') == u'the value of new_snapshot1.txt'

    assert_pytest_passes(testdir)  # assert that snapshot update worked


def test_assert_match_existing_snapshot_is_not_file(testdir, basic_case_dir):
    basic_case_dir.mkdir('directory1')
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match(u'something', 'directory1')
    """)
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        "E* AssertionError: snapshot exists but is not a file: case_dir?directory1",
    ])
    assert result.ret == 1

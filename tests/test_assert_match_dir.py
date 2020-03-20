import pytest

from tests.utils import assert_pytest_passes


@pytest.fixture
def basic_case_dir(testdir):
    case_dir = testdir.mkdir('case_dir')
    dict_snapshot1 = case_dir.mkdir('dict_snapshot1')
    dict_snapshot1.join('obj1.txt').write_text(u'the value of obj1.txt', 'ascii')
    dict_snapshot1.join('obj2.txt').write_text(u'the value of obj2.txt', 'ascii')
    return case_dir


def test_assert_match_dir_success(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match_dir({
                'obj1.txt': u'the value of obj1.txt',
                'obj2.txt': u'the value of obj2.txt',
            }, 'dict_snapshot1')
    """)
    assert_pytest_passes(testdir)


def test_assert_match_dir_failure(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match_dir({
                'obj1.txt': u'the value of obj1.txt',
                'obj2.txt': u'the INCORRECT value of obj2.txt',
            }, 'dict_snapshot1')
    """)
    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        ">* raise AssertionError(snapshot_diff_msg)",
        'E* AssertionError: value does not match the expected value in snapshot case_dir*dict_snapshot1*obj2.txt',
        "E* assert * == *",
        "E* - the value of obj2.txt",
        "E* + the INCORRECT value of obj2.txt",
        "E* ?    ++++++++++",
    ])
    assert result.ret == 1


def test_assert_match_dir_missing_snapshot(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match_dir({
                'obj1.txt': u'the value of obj1.txt',
                'obj2.txt': u'the value of obj2.txt',
                'new_obj.txt': u'the value of new_obj.txt',
            }, 'dict_snapshot1')
    """)
    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        "E* AssertionError: Values do not match snapshots in case_dir*dict_snapshot1",
        'E*   Values without snapshots:',
        'E*     new_obj.txt',
        'E*   Run pytest with --snapshot-update to update the snapshot directory.',
    ])
    assert result.ret == 1


def test_assert_match_dir_missing_value(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match_dir({
                'obj1.txt': u'the value of obj1.txt',
            }, 'dict_snapshot1')
    """)
    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        "E* AssertionError: Values do not match snapshots in case_dir*dict_snapshot1",
        'E*   Snapshots without values:',
        'E*     obj2.txt',
        'E*   Run pytest with --snapshot-update to update the snapshot directory.',
    ])
    assert result.ret == 1


def test_assert_match_dir_update_existing_snapshot_no_change(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match_dir({
                'obj1.txt': u'the value of obj1.txt',
                'obj2.txt': u'the value of obj2.txt',
            }, 'dict_snapshot1')
    """)
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth PASSED*',
    ])
    assert result.ret == 0


def test_assert_match_dir_update_existing_snapshot(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match_dir({
                'obj1.txt': u'the value of obj1.txt',
                'obj2.txt': u'the NEW value of obj2.txt',
            }, 'dict_snapshot1')
    """)
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth PASSED*',
        '*::test_sth ERROR*',
        "E* AssertionError: Snapshot directory was modified: case_dir",
        'E*   Updated snapshots:',
        'E*     dict_snapshot1*obj2.txt',
    ])
    assert result.ret == 1

    assert_pytest_passes(testdir)  # assert that snapshot update worked


def test_assert_match_dir_create_new_snapshot_file(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match_dir({
                'obj1.txt': u'the value of obj1.txt',
                'obj2.txt': u'the value of obj2.txt',
                'new_obj.txt': u'the value of new_obj.txt',
            }, 'dict_snapshot1')
    """)
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth PASSED*',
        '*::test_sth ERROR*',
        "E* AssertionError: Snapshot directory was modified: case_dir",
        'E*   Created snapshots:',
        'E*     dict_snapshot1*new_obj.txt',
    ])
    assert result.ret == 1

    assert_pytest_passes(testdir)  # assert that snapshot update worked


def test_assert_match_dir_delete_snapshot_file(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match_dir({
                'obj1.txt': u'the value of obj1.txt',
            }, 'dict_snapshot1')
    """)
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth PASSED*',
        '*::test_sth ERROR*',
        "E* AssertionError: Snapshot directory was modified: case_dir",
        'E*   Snapshots that should be deleted: (run pytest with --allow-snapshot-deletion to delete them)',
        'E*     dict_snapshot1*obj2.txt',
    ])
    assert result.ret == 1

    result = testdir.runpytest('-v', '--snapshot-update', '--allow-snapshot-deletion')
    result.stdout.fnmatch_lines([
        '*::test_sth PASSED*',
        '*::test_sth ERROR*',
        'E* AssertionError: Snapshot directory was modified: case_dir',
        'E*   Deleted snapshots:',
        'E*     dict_snapshot1*obj2.txt',
    ])
    assert result.ret == 1

    assert_pytest_passes(testdir)  # assert that snapshot update worked


def test_assert_match_dir_create_new_snapshot_dir(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match_dir({
                'obj1.txt': u'the value of obj1.txt',
            }, 'new_dict_snapshot')
    """)
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth PASSED*',
        '*::test_sth ERROR*',
        'E* AssertionError: Snapshot directory was modified: case_dir',
        'E*   Created snapshots:',
        'E*     new_dict_snapshot*obj1.txt',
    ])
    assert result.ret == 1

    assert_pytest_passes(testdir)  # assert that snapshot update worked


def test_assert_match_dir_existing_snapshot_is_not_dir(testdir, basic_case_dir):
    basic_case_dir.join('file1').write_text(u'', 'ascii')
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match_dir({}, 'file1')
    """)
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        "E* AssertionError: snapshot exists but is not a directory: case_dir*file1",
    ])
    assert result.ret == 1

import pytest


@pytest.fixture
def basic_case_dir(testdir):
    case_dir = testdir.mkdir('case_dir')
    case_dir.join('snapshot1.txt').write_text(u'the value of snapshot1.txt', 'ascii')
    return case_dir


def test_assert_match_success(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match(u'the value of snapshot1.txt', 'snapshot1.txt')
    """)
    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sth PASSED*',
    ])
    assert result.ret == 0


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
        'E* AssertionError: value does not match the expected value in snapshot case_dir*snapshot1.txt',
        "E* assert * == *",
        "E* - the value of snapshot1.txt",
        "E* + the INCORRECT value of snapshot1.txt",
        "E* ?    ++++++++++",
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
        "E* AssertionError: Snapshot 'snapshot_that_doesnt_exist.txt' doesn't exist in 'case_dir'.",
        'E* Run pytest with --snapshot-update to create it.',
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


def test_assert_match_update_existing_snapshot(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match(u'the NEW value of snapshot1.txt', 'snapshot1.txt')
    """)
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth PASSED*',
        '*::test_sth ERROR*',
        "E* AssertionError: The following snapshots were updated in 'case_dir':",
        'E*   snapshot1.txt'
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
        "E* AssertionError: The following snapshots were created in 'case_dir':",
        'E*   sub_dir*new_snapshot1.txt'
    ])
    assert result.ret == 1


def test_assert_match_existing_snapshot_is_directory(testdir, basic_case_dir):
    basic_case_dir.mkdir('directory1')
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match(u'something', 'directory1')
    """)
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        "E* AssertionError: invalid snapshot file case_dir*directory1",
    ])
    assert result.ret == 1

# -*- coding: utf-8 -*-
import pytest


@pytest.fixture
def basic_case_dir(testdir):
    case_dir = testdir.mkdir('case_dir')
    case_dir.join('snapshot1.txt').write_text(u'the value of snapshot1.txt', 'ascii')

def test_assert_match_success(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match('the value of snapshot1.txt', 'snapshot1.txt')
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
            snapshot.assert_match('the INCORRECT value of snapshot1.txt', 'snapshot1.txt')
    """)

    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        ">* assert expected_value == value",
        "E* AssertionError: assert 'the value of snapshot1.txt' == 'the INCORRECT * snapshot1.txt'",
        "E* - the value of snapshot1.txt",
        "E* + the INCORRECT value of snapshot1.txt",
        "E* ?    ++++++++++",
    ])
    assert result.ret == 1


def test_assert_match_missing_snapshot(testdir, basic_case_dir):
    testdir.makepyfile("""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match('something', 'snapshot_that_doesnt_exist.txt')
    """)

    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        "E* AssertionError: Snapshot 'snapshot_that_doesnt_exist.txt' doesn't exist in 'case_dir'.",
        'E* Run pytest with --snapshot-update to create it.',
    ])
    assert result.ret == 1


def test_help_message(testdir):
    result = testdir.runpytest(
        '--help',
    )
    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        'snapshot:',
        '*--snapshot-update*Update snapshots.',
    ])

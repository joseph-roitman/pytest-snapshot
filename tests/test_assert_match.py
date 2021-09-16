import os
from pathlib import Path

import pytest

from pytest_snapshot.plugin import _file_encode
from tests.utils import assert_pytest_passes


@pytest.fixture
def basic_case_dir(testdir):
    case_dir = testdir.mkdir('case_dir')
    case_dir.join('snapshot1.txt').write_text('the valuÉ of snapshot1.txt\n', 'utf-8')
    return case_dir


def test_assert_match_with_external_snapshot_path(testdir, basic_case_dir):
    testdir.makepyfile(r"""
        from pathlib import Path

        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match('the value of snapshot1.txt\n', Path('not_case_dir/snapshot1.txt').absolute())
    """)
    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        "E* AssertionError: Snapshot path not_case_dir?snapshot1.txt is not in case_dir",
    ])
    assert result.ret == 1


def test_assert_match_success_string(testdir, basic_case_dir):
    testdir.makepyfile(r"""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match('the valuÉ of snapshot1.txt\n', 'snapshot1.txt')
    """)
    assert_pytest_passes(testdir)


def test_assert_match_success_bytes(testdir, basic_case_dir):
    testdir.makepyfile(r"""
        import os
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match(b'the valu\xc3\x89 of snapshot1.txt' + os.linesep.encode(), 'snapshot1.txt')
    """)
    assert_pytest_passes(testdir)


def test_assert_match_failure_string(testdir, basic_case_dir):
    testdir.makepyfile(r"""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match('the INCORRECT value of snapshot1.txt\n', 'snapshot1.txt')
    """)
    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        ">* raise AssertionError(snapshot_diff_msg)",
        'E* AssertionError: value does not match the expected value in snapshot case_dir?snapshot1.txt',
        "E* assert * == *",
        "E* - the valuÉ of snapshot1.txt",
        "E* ?         ^",
        "E* + the INCORRECT value of snapshot1.txt",
        "E* ?    ++++++++++     ^",
    ])
    assert result.ret == 1


def test_assert_match_failure_bytes(testdir, basic_case_dir):
    testdir.makepyfile(r"""
        import os
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match(b'the INCORRECT value of snapshot1.txt' + os.linesep.encode(), 'snapshot1.txt')
    """)
    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        r'*::test_sth FAILED*',
        r">* raise AssertionError(snapshot_diff_msg)",
        r'E* AssertionError: value does not match the expected value in snapshot case_dir?snapshot1.txt',
        r"E* assert * == *",
        r"E* At index 4 diff: * != *",
        r"E* Full diff:",
        r"E* - b'the valu\xc3\x89 of snapshot1.txt{}'".format(repr(os.linesep)[1:-1]),
        r"E* + b'the INCORRECT value of snapshot1.txt{}'".format(repr(os.linesep)[1:-1]),
    ])
    assert result.ret == 1


def test_assert_match_invalid_type(testdir, basic_case_dir):
    testdir.makepyfile(r"""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match(123, 'snapshot1.txt')
    """)
    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        'E* TypeError: value must be str or bytes',
    ])
    assert result.ret == 1


def test_assert_match_missing_snapshot(testdir, basic_case_dir):
    testdir.makepyfile(r"""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match('something', 'snapshot_that_doesnt_exist.txt')
    """)
    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        "E* snapshot case_dir?snapshot_that_doesnt_exist.txt doesn't exist. "
        "(run pytest with --snapshot-update to create it)",
    ])
    assert result.ret == 1


def test_assert_match_update_existing_snapshot_no_change(testdir, basic_case_dir):
    testdir.makepyfile(r"""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match('the valuÉ of snapshot1.txt\n', 'snapshot1.txt')
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
    testdir.makepyfile(r"""
        from pathlib import Path

        def test_sth(snapshot):
            snapshot.snapshot_dir = {case_dir_repr}
            snapshot.assert_match('the NEW value of snapshot1.txt\n', {snapshot_name_repr})
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
    testdir.makepyfile(r"""
        from pathlib import Path

        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match('the NEW value of snapshot1.txt\n', 'snapshot1.txt')
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
    testdir.makepyfile(r"""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match('the NEW value of new_snapshot1.txt', 'sub_dir/new_snapshot1.txt')
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
    testdir.makepyfile(r"""
        def test_sth(snapshot):
            snapshot.assert_match('the value of new_snapshot1.txt', 'sub_dir/new_snapshot1.txt')
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
    ).read_text('utf-8') == 'the value of new_snapshot1.txt'

    assert_pytest_passes(testdir)  # assert that snapshot update worked


def test_assert_match_existing_snapshot_is_not_file(testdir, basic_case_dir):
    basic_case_dir.mkdir('directory1')
    testdir.makepyfile(r"""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match('something', 'directory1')
    """)
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        "E* AssertionError: snapshot exists but is not a file: case_dir?directory1",
    ])
    assert result.ret == 1


@pytest.mark.parametrize('tested_value', [
    b'',
    '',
    bytes(bytearray(range(256))),
    ''.join(chr(i) for i in range(0, 10000)).replace('\r', ''),
    '  \n \t \n  Whitespace!   \n\t  Whitespace!  \n  \t \n  ',
    # We don't support \r due to cross-compatibility and git by default modifying snapshot files...
    pytest.param('\r', marks=pytest.mark.xfail(strict=True)),
], ids=[
    'empty-bytes',
    'empty-string',
    'all-bytes',
    'unicode',
    'whitespace',
    'slash-r',
])
def test_assert_match_edge_cases(testdir, basic_case_dir, tested_value):
    """
    This test tests many possible values to snapshot test.
    This test will fail if we change the snapshot file format in any way.
    This test also checks that assert_match will pass after a snapshot update.
    """
    testdir.makepyfile(r"""
        def test_sth(snapshot):
            tested_value = {tested_value!r}
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match(tested_value, 'tested_value_snapshot')
    """.format(tested_value=tested_value))
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth PASSED*',
        '*::test_sth ERROR*',
    ])
    assert result.ret == 1

    if isinstance(tested_value, str):
        expected_encoded_snapshot = tested_value.replace('\n', os.linesep).encode()
    else:
        expected_encoded_snapshot = tested_value

    encoded_snapshot = Path(str(basic_case_dir)).joinpath('tested_value_snapshot').read_bytes()
    assert encoded_snapshot == expected_encoded_snapshot

    assert_pytest_passes(testdir)  # assert that snapshot update worked


def test_assert_match_unsupported_value_existing_snapshot(testdir, basic_case_dir):
    """
    Test that when running tests without --snapshot-update, we don't tell the user that the value is unsupported.
    We instead tell the user that the value does not equal the snapshot. This behaviour is more helpful.
    """
    basic_case_dir.join('newline.txt').write_binary(_file_encode('\n'))
    testdir.makepyfile(r"""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match('\r', 'newline.txt')
    """)
    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        'E* AssertionError: value does not match the expected value in snapshot case_dir?newline.txt',
        "E* - '\\n'",
        "E* + '\\r'",
    ])
    assert result.ret == 1


def test_assert_match_unsupported_value_update_existing_snapshot(testdir, basic_case_dir):
    basic_case_dir.join('newline.txt').write_binary(_file_encode('\n'))
    testdir.makepyfile(r"""
        import os
        from unittest import mock
        def _file_encode(string: str) -> bytes:
            return string.replace('\n', os.linesep).encode()

        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            with mock.patch('pytest_snapshot.plugin._file_encode', _file_encode):
                snapshot.assert_match('\r', 'newline.txt')
    """)
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        "E* ValueError: value is not supported by pytest-snapshot's serializer.",
    ])
    assert result.ret == 1


def test_assert_match_unsupported_value_create_snapshot(testdir, basic_case_dir):
    testdir.makepyfile(r"""
        import os
        from unittest import mock
        def _file_encode(string: str) -> bytes:
            return string.replace('\n', os.linesep).encode()

        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            with mock.patch('pytest_snapshot.plugin._file_encode', _file_encode):
                snapshot.assert_match('\r', 'newline.txt')
    """)
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        "E* ValueError: value is not supported by pytest-snapshot's serializer.",
    ])
    assert result.ret == 1


def test_assert_match_unsupported_value_slash_r(testdir, basic_case_dir):
    testdir.makepyfile(r"""
        def test_sth(snapshot):
            snapshot.snapshot_dir = 'case_dir'
            snapshot.assert_match('\r', 'newline.txt')
    """)
    result = testdir.runpytest('-v', '--snapshot-update')
    result.stdout.fnmatch_lines([
        '*::test_sth FAILED*',
        'E* ValueError: Snapshot testing strings containing "\\r" is not supported.',
    ])
    assert result.ret == 1

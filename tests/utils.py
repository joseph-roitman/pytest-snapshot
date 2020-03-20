def assert_pytest_passes(testdir):
    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines(['*::test_sth PASSED*'])
    assert result.ret == 0

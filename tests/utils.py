def runpytest_with_assert_mode(testdir, request, *args):
    """
    Calls `runpytest` if possible, otherwise calls `runpytest_subprocess`.

    Calling `runpytest` when the caller is run with --assert=rewrite and the callee is run with --assert=plain
    or vice versa does not work correctly, so this wrapper calls `runpytest_subprocess` in these cases.

    Note: If you are trying to debug a test that reaches `runpytest_subprocess`, consider running the test with another
    --assert mode.
    """
    if '--assert=plain' in args:
        assert_mode = 'plain'
    elif '--assert=rewrite' in args:
        assert_mode = 'rewrite'
    else:
        raise ValueError('Use this function only if you require --assert=rewrite or --assert=plain')

    if assert_mode == request.config.option.assertmode:
        return testdir.runpytest(*args)
    else:
        return testdir.runpytest_subprocess(*args)


def assert_pytest_passes(testdir):
    result = testdir.runpytest('-v')
    result.stdout.fnmatch_lines(['*::test_sth PASSED*'])
    assert result.ret == 0

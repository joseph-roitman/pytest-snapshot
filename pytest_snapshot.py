# -*- coding: utf-8 -*-

import pytest


def pytest_addoption(parser):
    group = parser.getgroup('snapshot')
    group.addoption(
        '--snapshot-update',
        action='store_true',
        help='Update snapshots.'
    )


@pytest.fixture
def snapshot(request):
    return Snapshot()


class Snapshot(object):
    pass

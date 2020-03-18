# -*- coding: utf-8 -*-

import pytest
from pathlib2 import Path
from typing import Optional


def pytest_addoption(parser):
    group = parser.getgroup('snapshot')
    group.addoption(
        '--snapshot-update',
        action='store_true',
        help='Update snapshots.'
    )

@pytest.fixture
def snapshot(request):
    return Snapshot(request.config.option.snapshot_update)


class Snapshot(object):

    _snapshot_update = None  # type: bool
    _snapshot_dir = None  # type: Optional[Path]

    def __init__(self, snapshot_update):
        self._snapshot_update = snapshot_update

    @property
    def snapshot_dir(self):
        if self._snapshot_dir is None:
            raise AssertionError('snapshot.snapshot_dir was not set.')
        return self._snapshot_dir
    
    @snapshot_dir.setter
    def snapshot_dir(self, value):
        self._snapshot_dir = Path(value)

    def _snapshot_path(self, snapshot_name):
        return self._snapshot_dir.joinpath(snapshot_name)
        
    def assert_match(self, value, snapshot_name):
        """
        Asserts that ``value`` equals the current value of the snapshot with the given ``snapshot_name``.

        If pytest was run with the --snapshot-update flag, the snapshot will instead be updated to ``value``.
        The test will fail if the value changed.

        :type value: str
        :type snapshot_name: str
        """
        if self._snapshot_update:
            raise NotImplementedError

        snapshot_path = self._snapshot_path(snapshot_name)
        if snapshot_path.exists():
            expected_value = snapshot_path.read_text()
            assert expected_value == value
        else:
            raise AssertionError("Snapshot '{}' doesn't exist in '{}'.\nRun pytest with --snapshot-update to create it.".format(snapshot_name, self.snapshot_dir))

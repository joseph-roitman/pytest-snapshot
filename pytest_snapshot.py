# -*- coding: utf-8 -*-

import pytest
from pathlib2 import Path
from typing import Optional, List


def pytest_addoption(parser):
    group = parser.getgroup('snapshot')
    group.addoption(
        '--snapshot-update',
        action='store_true',
        help='Update snapshots.'
    )

@pytest.fixture
def snapshot(request):
    with Snapshot(request.config.option.snapshot_update) as snapshot:
        yield snapshot


class Snapshot(object):

    _created_snapshots = None  # type: List[str]
    _updated_snapshots = None  # type: List[str]
    _snapshot_update = None  # type: bool
    _snapshot_dir = None  # type: Optional[Path]

    def __init__(self, snapshot_update):
        self._created_snapshots = []
        self._updated_snapshots = []
        self._snapshot_update = snapshot_update

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            return False
        if self._created_snapshots or self._updated_snapshots:
            message_lines = []
            if self._created_snapshots:
                message_lines.append("The following snapshots were created in '{}':".format(self._snapshot_dir))
                message_lines.extend('  ' + s for s in self._created_snapshots)

            if self._updated_snapshots:
                message_lines.append("The following snapshots were updated in '{}':".format(self._snapshot_dir))
                message_lines.extend('  ' + s for s in self._updated_snapshots)
            raise AssertionError('\n'.join(message_lines))

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
        snapshot_path = self._snapshot_path(snapshot_name)
        if self._snapshot_update:
            if snapshot_path.exists():
                if snapshot_path.read_text() != value:
                    snapshot_path.write_text(value)
                    self._updated_snapshots.append(snapshot_name)
            else:
                snapshot_path.write_text(value)
                self._created_snapshots.append(snapshot_name)
        else:
            if snapshot_path.exists():
                expected_value = snapshot_path.read_text()
                assert expected_value == value
            else:
                raise AssertionError("Snapshot '{}' doesn't exist in '{}'.\nRun pytest with --snapshot-update to create it.".format(snapshot_name, self.snapshot_dir))

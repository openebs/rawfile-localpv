import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from utils import task_manager
from utils.task_manager import TaskManager, TaskName, TaskState

MAX_RETRY = 3


@pytest.fixture
def calls(monkeypatch):
    calls = []

    def always_fails(*args, **kwargs):
        calls.append(args)
        raise FileNotFoundError(2, "No such file or directory")

    monkeypatch.setitem(task_manager.task_mapping, TaskName.CREATE_VOLUME, always_fails)
    return calls


@pytest.fixture
def manager(tmp_path):
    manager = TaskManager(
        ThreadPoolExecutor(max_workers=2),
        tasks_store_path=tmp_path / "tasks.json",
        retry_interval=0.01,
        max_retry=MAX_RETRY,
    )
    manager.start()
    yield manager
    manager.shutdown(timeout=1)


def wait_for(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_get_task_returns_saved_task(manager, calls):
    task_id = manager.run_task(TaskName.CREATE_VOLUME, "pvc-1")

    assert wait_for(lambda: manager.get_task(task_id) is not None)
    task = manager.get_task(task_id)
    assert task["task"] == TaskName.CREATE_VOLUME
    assert task["args"] == ["pvc-1"]


def test_failing_task_is_dropped_after_max_retry(manager, calls):
    task_id = manager.run_task(TaskName.CREATE_VOLUME, "pvc-1")

    assert wait_for(lambda: task_id not in manager.get_tasks())
    # retry_count starts at -1: the first run, then max_retry retries
    assert len(calls) == MAX_RETRY + 1
    # ...and no further retries once it was dropped
    time.sleep(0.1)
    assert len(calls) == MAX_RETRY + 1


def test_retry_keeps_last_error(manager, calls):
    task_id = manager.run_task(TaskName.CREATE_VOLUME, "pvc-1")

    assert wait_for(
        lambda: (manager.get_task(task_id) or {}).get("retry_ts") is not None
    )
    task = manager.get_task(task_id)
    assert "No such file or directory" in task.get("last_error", "")
    assert task["retry_count"] >= 0


def test_duplicate_request_does_not_rerun_pending_task(tmp_path, monkeypatch):
    calls = []

    def slow(*args, **kwargs):
        calls.append(args)
        time.sleep(0.2)

    monkeypatch.setitem(task_manager.task_mapping, TaskName.CREATE_VOLUME, slow)
    manager = TaskManager(
        ThreadPoolExecutor(max_workers=2),
        tasks_store_path=tmp_path / "tasks.json",
        retry_interval=0.01,
    )
    manager.start()
    try:
        first = manager.run_task(TaskName.CREATE_VOLUME, "pvc-1")
        second = manager.run_task(TaskName.CREATE_VOLUME, "pvc-1")

        assert first == second
        assert wait_for(lambda: first not in manager.get_tasks())
        assert len(calls) == 1
        assert manager.get_tasks(state=TaskState.FAILED) == {}
    finally:
        manager.shutdown(timeout=1)


def write_task(tasks_store_path, state):
    task = {
        "task": TaskName.CREATE_VOLUME,
        "args": ["pvc-1"],
        "kwargs": {},
        "retry_count": 0,
        "state": state,
    }
    tasks_store_path.write_text(json.dumps({"task-1": task}))


def unstarted_manager(tasks_store_path):
    return TaskManager(
        ThreadPoolExecutor(max_workers=2),
        tasks_store_path=tasks_store_path,
        retry_interval=0.01,
        max_retry=MAX_RETRY,
    )


def test_failed_tasks_are_not_retried_before_start(tmp_path, calls):
    # The startup checks and migrations run before start() and must not race
    # task retries
    write_task(tmp_path / "tasks.json", TaskState.FAILED)
    manager = unstarted_manager(tmp_path / "tasks.json")
    try:
        time.sleep(0.1)
        assert calls == []

        manager.start()

        assert wait_for(lambda: len(calls) > 0)
        assert calls[0] == ("pvc-1",)
    finally:
        manager.shutdown(timeout=1)


def test_start_recovers_tasks_interrupted_by_a_crash(tmp_path, calls):
    manager = unstarted_manager(tmp_path / "tasks.json")
    try:
        # e.g. the tasks file was moved in place by the startup migrations
        write_task(tmp_path / "tasks.json", TaskState.RUNNING)

        manager.start()

        assert wait_for(lambda: len(calls) > 0)
        assert calls[0] == ("pvc-1",)
    finally:
        manager.shutdown(timeout=1)

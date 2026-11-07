# Task Manager Design Document

## System Overview

The Task Manager is a robust system for handling asynchronous task execution with state persistence, retry capabilities, and graceful shutdown handling. It's currently integrated with snapshot management functionality.

## Core Components

### 1. Task States

```python
class TaskState(StrEnum):
    PENDING = "Pending"
    RUNNING = "Running"
    FAILED = "Failed"
    COMPLETED = "Completed"
```

### 2. Task Information Structure

```python
class TaskInfo(TypedDict):
    task: str  # Task name/identifier
    args: list  # Positional arguments
    kwargs: dict  # Keyword arguments
    retry_count: int  # Number of retry attempts
    state: TaskState  # Current state of task
```

### 3. Key Features

#### State Management

- **Persistent Storage**
  - Tasks stored in JSON format at `{DATA_DIR}/tasks.json`
  - Thread-safe operations using Lock mechanism
  - Automatic state recovery after crashes
  - Handles stuck tasks by marking them as failed when the Task Manager is started

#### Task Execution

- Asynchronous execution using provided executor
- Task identification using MD5 hash of task parameters
- Current supported tasks:

  ```python
  class TaskName(StrEnum):
      CREATE_SNAPSHOT = "CreateSnapshot"
  ```

#### Retry Mechanism

- Configurable retry settings:
  - Retry interval (default: 5 seconds)
  - Maximum retries (default: 5 attempts)
- Automatic retry for failed tasks
- Cleanup of non-retriable and completed tasks

## Technical Implementation

### 1. Thread Safety

- Uses `threading.Lock` for file operations
- Ensures atomic operations on task storage

### 2. Task Lifecycle

1. Task submission
2. State transitions: PENDING → RUNNING → COMPLETED/FAILED
3. Automatic retry for failed tasks
4. Cleanup of completed/non-retriable tasks

### 3. Startup Process

- Creating the Task Manager neither runs nor retries any task
- `start()` marks the tasks left running by a crash as failed and starts the retry worker
- The node plugin calls it after its startup checks and migrations (which also move `tasks.json` into place), right before serving requests:
  - the migrations rewrite volume metadata, so they must not race retried tasks
  - a running retry worker keeps the process from exiting, so a failed startup would hang instead of being restarted

### 4. Shutdown Process

- Graceful shutdown with timeout
- Marks running tasks as failed
- Cancels pending futures
- Preserves task states

## Error Handling

- Custom `TaskManagerShuttingDown` exception
- Automatic crash recovery
- Task state preservation
- Exception logging with context

## Usage Example

```python
task_manager = TaskManager(executor, tasks_store_path, retry_interval=5, max_retry=5)
task_manager.start()
task_id = task_manager.run_task(TaskName.CREATE_SNAPSHOT, *args, **kwargs)
```

# Analysis Service Core

A core library for building analysis pipeline runners in the Echolalia analysis service stack. Provides abstractions for task lifecycle management, progress tracking, Redis-based messaging, and metadata generation.

## Features

### 🚀 **ModelPlugin Framework**
- Abstract base class for analysis pipeline implementations
- Automatic task queue polling and lifecycle management
- Input group discovery and processing with error recovery
- Progress reporting and completion signaling
- Built-in resume functionality to skip completed work
- Directory-based filtering for concurrent processing

### 📊 **Progress Tracking**
- `EffortModel` abstraction for defining task complexity and progress
- Automatic progress calculation based on completed vs. total work
- Real-time progress reporting via Redis pub/sub

### 📨 **Redis Integration** 
- Command abstraction for Redis queue messages (`RunTask`, `CompleteTask`, `ReportProgress`)
- JSON serialization with proper handling of optional fields
- Queue and pub/sub utilities for service communication

### 📄 **Metadata Generation**
- `MetannotsFactory` for generating standardized metadata files
- Automatic system metadata (date, package version)
- Extensible for model-specific metadata requirements

### 🔄 **Task Control**
- **Resume mode**: Automatically skip completed input groups and clean up incomplete outputs
- **Directory filtering**: Process only files within specified subdirectories  
- **Error isolation**: Individual input group failures don't stop the entire task

## Quick Start

### 1. Implement your EffortModel

```python
from analysis_service_core.src.effort_model import EffortModel

class MyEffortModel(EffortModel):
    def find_igroups(self, dataset_dir: Path) -> List[InputGroup]:
        # Discover input file groups to process
        return [[f] for f in dataset_dir.glob("*.wav")]
    
    def pogroup_from_igroup(self, dataset_dir, output_dir, igroup):
        # Define expected pass outputs for each input group
        return [output_dir / f"{igroup[0].stem}.txt"]
    
    def ogroup_from_pogroup(self, dataset_dir, output_dir, pogroup, igroup):
        # Define final outputs after postprocessing
        return pogroup  # Same as pass outputs
    
    def effort_pogroup_from_igroup(self, igroup, pogroup):
        # Calculate processing effort (for progress tracking)
        return len(igroup)
```

### 2. Implement your ModelPlugin

```python
from analysis_service_core.src.model import ModelPlugin

class MyModel(ModelPlugin):
    def run_model(self, dataset_dir: Path, output_dir: Path, igroup: InputGroup) -> None:
        # Run your analysis on the input group
        input_file = igroup[0]
        output_file = output_dir / f"{input_file.stem}.txt"
        
        # Your model logic here
        result = analyze(input_file)
        output_file.write_text(result)
    
    def postprocess(self, dataset_dir: Path, output_dir: Path, pogroup: PassOutputGroup, igroup: InputGroup) -> None:
        # Optional: transform pass outputs into final outputs
        for po_file in pogroup:
            # Copy or transform as needed
            pass
```

### 3. Create MetannotsFactory (optional)

```python
from analysis_service_core.src.metannots import MetannotsFactory

class MyMetannotsFactory(MetannotsFactory):
    def get_default_values(self) -> Dict[str, Any]:
        return {
            'segmentation': 'voice_activity',
            'method': 'automated',
            'annotation_algorithm_name': 'MyModel',
            'annotation_algorithm_version': '1.0',
            # ... other metadata
        }
    
    def get_task_values(self, run_task: RunTask) -> Dict[str, Any]:
        # Extract task-specific parameters when available
        return {}
```

### 4. Run your model

```python
from analysis_service_core.src.redis.queue import Queue, QueueName
from analysis_service_core.src.config import Config

# Initialize
queue = Queue(QueueName.RUN_VTC)  # Or your queue name
config = Config()
effort_model = MyEffortModel()
metannots_factory = MyMetannotsFactory()

# Create model instance
model = MyModel(
    queue=queue,
    config=config, 
    effort_model=effort_model,
    metannots_factory=metannots_factory
)

# Start processing (blocks until task received)
model.run()
```

## Command Features

### RunTask Options
- `directory`: Process only files within a specific subdirectory
- `resume`: Skip completed work and clean up partial outputs (default: `True`)

```python
# Process only files in /dataset/subfolder
RunTask(
    task_id=uuid4(),
    dataset_uid_label="my_dataset",
    operation=Operation.RUN_MY_MODEL,
    directory=Path("/dataset/subfolder")
)

# Run from scratch (don't resume)
RunTask(
    task_id=uuid4(),
    dataset_uid_label="my_dataset", 
    operation=Operation.RUN_MY_MODEL,
    resume=False
)
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Redis Queue   │    │  ModelPlugin    │    │  EffortModel    │
│                 │───▶│                 │───▶│                 │
│ RunTask msgs    │    │ Task lifecycle  │    │ Progress calc   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │MetannotsFactory │
                       │                 │
                       │ Metadata gen    │
                       └─────────────────┘
```

## Testing

The library provides three testing mixins covering the full testing pyramid for any `ModelPlugin` implementation.

### EffortModel Testing

Validates that an `EffortModel` correctly discovers igroups and maps them to the right pogroups, ogroups, and effort values — without running any model code.

```python
from analysis_service_core.testing.mixins import EffortModelTestBase
from analysis_service_core.testing.mocks import ConfigMock

class TestMyEffortModel(EffortModelTestBase):
    effort_model_cls = MyEffortModel
    config = ConfigMock()
    datasets_dir = Path(__file__).parent / "test_datasets"
    expected_forward_passes_json = Path(__file__).parent / "expected.json"
```

The `expected.json` describes each forward pass. `igroup` paths are relative to `stage_0/`. `pogroup` and `ogroup` paths are relative to the output directory inside `stage_0/` (i.e. `stage_0/outputs/<task_id>/`):

```json
[
    {
        "igroup": ["words/converted/child_1/words_1_1.txt"],
        "pogroup": ["child_1/words_1_1.txt", "child_1/date.txt"],
        "ogroup": ["child_1/words_1_1.txt"],
        "pass_effort": 3.0,
        "output_effort": 0.5
    }
]
```

Automatically tests igroup discovery, pogroup/ogroup mapping, and effort calculation.

### Model Integration Testing

Runs `run_model` and `postprocess` directly against a real filesystem, with Redis and pubsub mocked out. Uses three stage snapshots of the full dataset directory to verify the pipeline produces exactly the right file tree at each stage.

```python
from analysis_service_core.testing.mixins import ModelIntegrationTestBase
from analysis_service_core.testing.mocks import ConfigMock

class TestMyModelIntegration(ModelIntegrationTestBase):
    model_cls = MyModel
    effort_model_cls = MyEffortModel
    queue_name = QueueName.RUN_MY_MODEL
    config = ConfigMock()
    datasets_dir = Path(__file__).parent / "test_datasets"
```

`datasets_dir` must contain three subdirectories, each a complete snapshot of the dataset at a pipeline stage:

| Directory | Contents |
|-----------|----------|
| `stage_0/` | Initial state — input files only |
| `stage_1/` | State after all `run_model` calls — inputs + pass outputs under `outputs/<task_id>/` |
| `stage_2/` | State after all `postprocess` calls — inputs + final outputs under `outputs/<task_id>/` |

The output directory inside each snapshot is `outputs/<task_id>/`, matching the path that `get_final_output_dir` produces in production. The test copies `stage_0/` into a temp directory and uses it as the live dataset throughout the run.

Two optional hooks let subclasses customize setup per test:

```python
def make_config(self, temp_dataset: Path) -> Config:
    """Return a config pointing at the temp dataset. Override when your model
    reads paths from config (e.g. datasets_dir)."""
    return ConfigMock(overrides={"datasets_dir": str(temp_dataset.parent)})

def prepare_temp_dataset(self, temp_dataset: Path) -> None:
    """Create any directories or files the model needs before running."""
    (temp_dataset / "scratch").mkdir()
```

Automatically tests full pipeline execution and that the dataset file tree matches `stage_1` after `run_model` and `stage_2` after `postprocess`.

### E2E Testing

Builds the worker Docker image, spins up a Redis container via testcontainers, enqueues a real `RunTask`, and waits for `CompleteTask`. Tests the full production code path including queue polling, the complete task lifecycle, and pub/sub progress reporting.

```python
from analysis_service_core.testing.mixins import ModelE2ETestBase

class TestMyModelE2E(ModelE2ETestBase):
    queue_name = QueueName.RUN_MY_MODEL
    operation = Operation.RUN_MY_MODEL
    dockerfile = Path(__file__).parent / "Dockerfile"
    datasets_dir = Path(__file__).parent / "datasets"
    echolalia_dir = Path(__file__).parent / "echolalia"
    DATASET_UID = UUID("...")
    worker_env = {"MY_ENV_VAR": "value"}
    effort_model_cls = MyEffortModel
    TEST_IDEMPOTENCY = True
```

Optional class attributes:

| Attribute | Default | Description |
|-----------|---------|-------------|
| `build_context` | `dockerfile.parent` | Docker build context root |
| `extra_volume_mounts` | `[]` | Additional `(host_path, container_path)` mounts |
| `SUBDIRECTORY` | `None` | Limit the task to a dataset subdirectory |
| `TEST_IDEMPOTENCY` | `False` | Run the task twice and assert the output tree is identical |
| `TIMEOUT` | `1000` | Seconds to wait for task completion |

Automatically tests that the output directory contains files, `metannots.yml` was written, progress messages were published, and the final progress message reports all passes complete.

## Requirements

- Python 3.13+
- Redis server
- PyYAML for metadata generation

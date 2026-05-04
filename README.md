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

The library includes comprehensive testing mixins for validating your implementations:

### EffortModel Testing

```python
from analysis_service_core.testing.mixins.effort_model_test_base import EffortModelTestBase

class TestMyEffortModel(EffortModelTestBase):
    effort_model_cls = MyEffortModel
    datasets_dir = Path(__file__).parent / "test_datasets"
    expected_forward_passes_json = Path(__file__).parent / "expected.json"
    
    # Automatically tests:
    # - igroups discovery matches expectations
    # - pogroup/ogroup mapping correctness  
    # - effort calculations match expected values
```

### Model Integration Testing

```python
from analysis_service_core.testing.mixins.model_integration_test_base import ModelIntegrationTestBase

class TestMyModelIntegration(ModelIntegrationTestBase):
    model_cls = MyModel
    effort_model_cls = MyEffortModel
    queue_name = QueueName.RUN_MY_MODEL
    config = Config()
    datasets_dir = Path(__file__).parent / "test_datasets"
    
    # Automatically tests:
    # - Full pipeline execution
    # - Output file generation
    # - Progress reporting
    # - Error handling per input group
```

## Requirements

- Python 3.13+
- Redis server
- PyYAML for metadata generation

# AWS CLI Linter

A CLI tool that lints bash scripts for AWS CLI v1 usage and updates them to avoid breaking changes introduced in AWS CLI v2.

## Installation

1. Create a virtual environment:
```bash
python3.12 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
# Or use lockfile for reproducible builds:
pip install -r requirements.lock
```

3. Install the package in development mode:
```bash
pip install -e .
```

## Usage

### Dry-run mode (default)
Display issues without modifying the script:
```bash
upgrade-aws-cli --script upload_s3_files.sh
```

### Fix mode
Automatically update the input script:
```bash
upgrade-aws-cli --script upload_s3_files.sh --fix
```

### Output mode
Create a new fixed script without modifying the original:
```bash
upgrade-aws-cli --script upload_s3_files.sh --output upload_s3_files_v2.sh
```

### Interactive mode
Review and accept/reject each change individually:
```bash
upgrade-aws-cli --script upload_s3_files.sh --interactive --output upload_s3_files_v2.sh
```

In interactive mode, you can:
- Press `y` to accept the current change
- Press `n` to skip the current change
- Press `u` to accept all remaining changes
- Press `x` to cancel and exit

Note: `--interactive` requires either `--output` to specify where to write changes, or no output flag for dry-run. It cannot be used with `--fix`.

## Development

### Running tests
```bash
pytest
```

### Code formatting
```bash
black awsclilinter tests
isort awsclilinter tests
```

## Adding New Linting Rules

To add a new linting rule:

1. Create a new rule class in `awsclilinter/rules/` that inherits from `LintRule`
2. Implement the required methods: `name`, `description`, and `check`
3. Add the rule to the rules list in `awsclilinter/cli.py`

Example:
```python
from awsclilinter.rules_base import LintRule, LintFinding

class MyCustomRule(LintRule):
    @property
    def name(self) -> str:
        return "my-custom-rule"
    
    @property
    def description(self) -> str:
        return "Description of what this rule checks"
    
    def check(self, root) -> List[LintFinding]:
        # Implementation using ast-grep
        pass
```

## Architecture

- `rules_base.py`: Base classes for linting rules (`LintRule`, `LintFinding`)
- `rules/`: Directory containing individual linting rule implementations
- `linter.py`: Main `ScriptLinter` class that orchestrates rule checking
- `cli.py`: CLI interface using argparse
- `tests/`: Unit tests using pytest

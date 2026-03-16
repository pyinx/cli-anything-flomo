# CLI-Anything Harness Specification

## Overview

This document defines the complete methodology, architecture standards, and implementation patterns for building production-ready CLI harnesses for GUI applications. All phases follow this specification.

## Architecture Principles

### 1. Namespace Package Structure

```
agent-harness/
├── <SOFTWARE>.md              # Software-specific SOP
├── setup.py                   # PyPI package config
├── README.md                  # Installation and usage
└── cli_anything/              # Namespace package (NO __init__.py - PEP 420)
    └── <software>/            # Sub-package (HAS __init__.py)
        ├── __init__.py
        ├── <software>_cli.py  # Main CLI entry point
        ├── core/              # Core business logic modules
        │   ├── __init__.py
        │   ├── auth.py        # Authentication
        │   ├── session.py     # Session management
        │   ├── project.py     # Project/document operations
        │   └── export.py      # Export functionality
        ├── utils/             # Shared utilities
        │   ├── __init__.py
        │   ├── api.py         # API client
        │   ├── config.py      # Configuration management
        │   └── output.py      # Output formatting
        └── tests/
            ├── TEST.md        # Test plan and results
            ├── test_core.py   # Unit tests
            └── test_full_e2e.py # E2E tests
```

### 2. Package Naming Convention

- **PyPI Package**: `cli-anything-<software>` (e.g., `cli-anything-flomo`)
- **Import Namespace**: `cli_anything.<software>` (e.g., `cli_anything.flomo`)
- **CLI Command**: `cli-anything-<software>` (e.g., `cli-anything-flomo`)

### 3. setup.py Configuration

```python
from setuptools import setup, find_namespace_packages

setup(
    name='cli-anything-<software>',
    version='0.1.0',
    packages=find_namespace_packages(include=['cli_anything.*']),
    install_requires=[
        'click>=8.0',
        'requests>=2.28.0',
        # Add other dependencies
    ],
    entry_points={
        'console_scripts': [
            'cli-anything-<software>=cli_anything.<software>.<software>_cli:main',
        ],
    },
    python_requires='>=3.8',
)
```

**CRITICAL**:
- `cli_anything/` directory has NO `__init__.py` (PEP 420 namespace package)
- `cli_anything/<software>/` directory HAS `__init__.py`
- Use `find_namespace_packages(include=['cli_anything.*'])`

## Implementation Standards

### 1. CLI Design Pattern

Use Click with REPL support:

```python
import click
import json
from typing import Optional

@click.group()
@click.option('--json', 'output_json', is_flag=True, help='Output in JSON format')
@click.pass_context
def cli(ctx, output_json):
    """CLI for <Software> - Description"""
    ctx.ensure_object(dict)
    ctx.obj['json'] = output_json

@cli.command()
@click.argument('content')
@click.option('--tag', '-t', multiple=True, help='Tags for the memo')
@click.pass_context
def create(ctx, content, tag):
    """Create a new item"""
    # Implementation
    pass

def main():
    cli(obj={})

if __name__ == '__main__':
    main()
```

### 2. Output Formatting

Always support `--json` mode for agent consumption:

```python
def format_output(data, is_json):
    if is_json:
        click.echo(json.dumps(data, indent=2))
    else:
        # Human-readable format
        click.echo(format_human(data))
```

### 3. State Management

Store configuration and state in standard locations:

- **Config**: `~/.config/cli-anything-<software>/config.json`
- **Cache**: `~/.cache/cli-anything-<software>/`
- **Data**: `~/.local/share/cli-anything-<software>/`

### 4. Error Handling

Use structured error messages:

```python
class CLIError(Exception):
    """Base CLI error"""
    pass

def handle_error(error, is_json):
    if is_json:
        click.echo(json.dumps({'error': str(error)}), err=True)
    else:
        click.secho(f"Error: {error}", fg='red', err=True)
    raise SystemExit(1)
```

## Testing Standards

### 1. Unit Tests (test_core.py)

- Test core logic in isolation
- Use mock data, no external dependencies
- Test all public functions and methods
- Aim for >90% code coverage

```python
import pytest
from cli_anything.<software>.core import auth

def test_authenticate_success():
    # Test with valid credentials
    pass

def test_authenticate_failure():
    # Test with invalid credentials
    pass
```

### 2. E2E Tests (test_full_e2e.py)

- Test complete workflows
- Use real API calls (with test credentials)
- Verify outputs and side effects
- Include cleanup procedures

```python
import pytest
import subprocess
import os

class TestCLISubprocess:
    def _resolve_cli(self, cmd):
        """Resolve CLI command - respects CLI_ANYTHING_FORCE_INSTALLED"""
        if os.environ.get('CLI_ANYTHING_FORCE_INSTALLED'):
            return cmd
        # Fallback to module execution
        return f'python -m cli_anything.<software>.<software>_cli'

    def test_create_and_delete(self):
        cli = self._resolve_cli('cli-anything-<software>')
        result = subprocess.run(
            [cli, 'create', 'test content'],
            capture_output=True
        )
        assert result.returncode == 0
```

### 3. Test Documentation (TEST.md)

Structure:
1. **Test Plan**: What to test and why
2. **Test Coverage**: Modules and functions covered
3. **Test Results**: Full pytest output
4. **Known Issues**: Gaps and limitations

## Implementation Phases

### Phase 0: Source Acquisition
- Clone repository or verify local path
- Identify software type (Electron, native, web app)
- Document version and dependencies

### Phase 1: Codebase Analysis
- Analyze application architecture
- Identify API endpoints and data models
- Map GUI actions to API calls
- Document authentication mechanism
- Identify existing CLI tools

### Phase 2: CLI Architecture Design
- Define command groups matching app domains
- Design state model and configuration
- Plan output formats (text, JSON, table)
- Create software-specific SOP document

### Phase 3: Implementation
- Create directory structure
- Implement core modules
- Build CLI with Click
- Add REPL support
- Implement --json output
- Add error handling

### Phase 4: Test Planning
- Create TEST.md
- Plan unit tests for all modules
- Plan E2E tests with real data
- Design workflow scenarios

### Phase 5: Test Implementation
- Write unit tests
- Write E2E tests
- Implement workflow tests
- Add output verification

### Phase 6: Test Documentation
- Run all tests with `pytest -v --tb=no`
- Append results to TEST.md
- Document coverage
- Note any gaps

### Phase 7: PyPI Publishing
- Create setup.py
- Configure entry points
- Test local installation: `pip install -e .`
- Verify CLI in PATH: `which cli-anything-<software>`
- Test via subprocess with `CLI_ANYTHING_FORCE_INSTALLED=1`

## Success Criteria

A CLI harness is complete when:

1. ✅ All core modules implemented and functional
2. ✅ CLI supports one-shot commands and REPL mode
3. ✅ `--json` output works for all commands
4. ✅ All tests pass (100% pass rate)
5. ✅ Subprocess tests use `_resolve_cli()` and pass
6. ✅ TEST.md contains plan and results
7. ✅ README.md documents installation and usage
8. ✅ setup.py created and local install works
9. ✅ CLI available in PATH as `cli-anything-<software>`

## Code Quality Standards

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Add docstrings to all public APIs
- Keep functions focused and testable
- Handle errors gracefully
- Provide helpful error messages
- Support both interactive and scripted usage

## Security Considerations

- Never log sensitive data (tokens, passwords)
- Store credentials securely (keyring or encrypted)
- Validate all user input
- Use HTTPS for all API calls
- Implement rate limiting where appropriate
- Follow principle of least privilege

# Testing Guide

## Quick Commands

### Run all tests
```bash
pytest tests/
```

### Run with verbose output
```bash
pytest tests/ -v
```

### Run specific test file
```bash
pytest tests/test_token_replacement_fixes.py
```

### Run specific test function
```bash
pytest tests/test_token_replacement_fixes.py::test_find_corrupted_token
```

### Run with coverage report
```bash
pytest tests/ --cov=rules_based_replacements --cov=translate
```

## PyCharm Configuration

### Method 1: Auto-detect (Easiest)

1. Right-click on the `tests` folder in PyCharm
2. Select "Run 'pytest in tests'"
3. PyCharm will automatically detect pytest and create a configuration

### Method 2: Manual Configuration

1. Click "Add Configuration" (top right, near play button)
2. Click "+" → "pytest"
3. Name: "pytest (all tests)"
4. Configuration:
   - **Target:** Module (select `tests` directory)
   - **Working directory:** `C:\Users\CARRK\Documents\Repositories\AI\Pipeline`
   - **Python interpreter:** Project interpreter (.venv)
   - **Additional Arguments:** `-v` (for verbose output)
5. Click "OK"
6. Run with play button or Shift+F10

### Run Individual Tests in PyCharm

Once pytest is configured:
- Open a test file
- You'll see green play icons next to each test function
- Click any play icon to run that specific test
- Right-click on a test to debug it

## Test Structure

Tests are located in `tests/` directory:
- `test_token_replacement_fixes.py` - Tests for token replacement improvements

## Configuration Files

- `pytest.ini` - pytest configuration
- `.pytest_cache/` - cached test results (gitignored)

## Adding New Tests

1. Create a file named `test_*.py` in the `tests/` directory
2. Write test functions starting with `test_`
3. Use `assert` statements for validation
4. pytest will automatically discover and run them

Example:
```python
def test_my_feature():
    result = my_function()
    assert result == expected_value
```

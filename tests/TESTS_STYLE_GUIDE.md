# Guide for professional-grade `pytest` suites.

## 1. Structure and Discovery

* **Decouple Logic:** Keep tests in a `tests/` directory mirroring your `src/` structure.
* **Conftest Power:** Use `conftest.py` for shared fixtures to keep individual test files focused on logic rather than setup.
* **Naming:** Use `test_*.py` for files, `Test*` for classes, and `test_*` for functions to ensure automatic discovery.

## 2. Fixture Management

* **Explicit over Implicit:** Avoid `autouse=True` unless necessary (e.g., DB cleanup). Explicitly injecting fixtures makes dependencies clear for refactoring.
* **Scoping:** Use the narrowest possible scope (`function`, `class`, `module`, `session`) to optimize performance.
* **Yield for Teardown:** Use `yield` instead of `addfinalizer` for a cleaner "setup-action-teardown" flow.

```py
@pytest.fixture
def db_connection():
    conn = setup_db()
    yield conn
    conn.close()
```

## 3. Pattern: AAA (Arrange, Act, Assert)

Maintain a clear visual separation between the setup, the execution, and the verification.

* **Arrange:** Set up the object, mocks, or data.
* **Act:** Call the single method or function being tested.
* **Assert:** Verify the outcome. Limit this to one logical concept per test.

## 4. Parametrization for Extendibility

Instead of writing multiple tests for different inputs, use `@pytest.mark.parametrize`. This allows adding new test cases by simply adding a tuple to a list.

```py
@pytest.mark.parametrize("input_val, expected", [
    (1, 2),
    (5, 6),
    (10, 11),
])
def test_increment(input_val, expected):
    assert increment(input_val) == expected
```

## 5. Mocking and Patching

* **Prefer `pytest-mock`:** Use the `mocker` fixture instead of `unittest.mock.patch`. It handles teardown automatically and is less verbose.
* **Mock at the Target:** Always patch where the object is *imported*, not where it is defined.

## 6. Assertion Best Practices

* **Use `pytest.raises`:** For testing exceptions, use the context manager to ensure the specific error type and message are caught.

```py
with pytest.raises(ValueError, match="Invalid ID"):
    process_data(-1)
```

* **Custom Assertions:** If you find yourself repeating complex dictionary or object comparisons, move them into a helper function or a custom `pytest_assertrepr_compare` hook.

## 7. Configuration and Marks

* **`pytest.ini`:** Define your `testpaths`, `pythonpath`, and custom `markers` here to avoid warnings.
* **Categorization:** Use `@pytest.mark.smoke` or `@pytest.mark.integration` to allow running specific subsets of tests via `pytest -m smoke`.

## 8 .Recommended Repository Structure

In a standard Python project, the `conftest.py` file should be stored in your root `tests/` directory to be globally accessible to all test modules.

```text
your-repo/
├── pyproject.toml       # or pytest.ini
├── src/
│   └── calculator.py
└── tests/
    ├── conftest.py      # Global fixtures & hooks
    ├── test_core.py     # Functional tests
    └── integration/
        └── test_api.py  # Sub-directory for specific suites

```

## 7. Global `conftest.py` (The Template)

Use this for shared resources like database engines, API clients, or mock user data.

```
your-repo/
├── pyproject.toml       # or pytest.ini
├── src/
│   └── calculator.py
└── tests/
    ├── conftest.py      # Global fixtures & hooks
    ├── test_core.py     # Functional tests
    └── integration/
        └── test_api.py  # Sub-directory for specific suites
```

## 10. Sample Test Class (`tests/test_core.py`)

This follows the **Arrange, Act, Assert** pattern and uses the fixtures defined above.

```py
import pytest


class TestCalculator:
    @pytest.mark.parametrize("a, b, expected", [
        (1, 2, 3),
        (5, 5, 10),
        (-1, 1, 0)
    ])
    def test_addition(self, a, b, expected):
        from src.calculator import add
        result = add(a, b)
        assert result == expected
    
    def test_division_by_zero(self):
        from src.calculator import divide
        with pytest.raises(ZeroDivisionError, match="division by zero"):
            divide(10, 0)

```

### 3. Configuration (`pyproject.toml`)

Registering marks here prevents "unknown mark" warnings and enforces strict testing.

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "serial",
]
```

## Project-Specific Conventions

### Shared Fixtures (`conftest.py`)

* **`MockTranslator`:** Use the shared `MockTranslator` from `conftest.py` (prefix `[TR:...]`). Do not redefine it in individual test files.
* **`run_word_translation(fixture_name, source_lang, mock=None)`:** Handles temp file creation/cleanup and JSON notes loading. Returns `(doc, mock, notes_data)`.
* **`all_notes_text(notes_data)`:** Flattens JSON notes into a single string for substring searches.
* **`notes_entry_count(notes_data)`:** Returns total entries across paragraphs + tables sections.

### Notes Format

Translation notes are JSON (`_translation_notes.json`), not `.docx`. When asserting on notes content, work with the dict structure:

```py
# Check if a paragraph has a note
has_note = any(
    prefix in entry['full_paragraph']
    for section in ['paragraphs', 'tables']
    for entry in notes_data.get(section, [])
)
```

### Markers

* **`@pytest.mark.slow`:** Tests that load real ML models (e.g., mbart). Deselect with `-m "not slow"`.

### Module-Scoped Fixtures for Expensive Setup

When multiple tests share the same translated document, use `scope="module"` to avoid re-running the translation:

```py
@pytest.fixture(scope="module")
def translated():
    return run_word_translation('fixture.docx', 'en')
```

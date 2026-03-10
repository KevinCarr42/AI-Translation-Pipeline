# Style Guide

## 1. Architecture & Design Patterns

### The Rule Registry (Strategy Pattern)

- Why: Decouples the execution of formatting rules from the traversal logic, allowing new rules to be added without modifying core loops.
- How: Create a new class inheriting from `FormattingRule`. Implement the `detect` and `apply` methods. Decorate the class with `@RuleRegistry.register`.
- Rule: Never hardcode formatting checks (`if is_bold: ... elif is_italic: ...`) inside the main translation loops.

### Generators for Traversal

- Why: Flattens deeply nested data structures (like Word document paragraphs, tables, and headers) into a single, iterable stream.
- How: Use `yield` to emit elements and their metadata dictionary.
- Rule: Do not write nested `for` loops in the main execution blocks; delegate traversal to a dedicated generator function like `_iter_document_elements`.

## 2. Code Structure & State Management

### Separation of Concerns (Pure Functions)

- Why: Makes logic easily testable without requiring heavy mocking of disk I/O or `lxml` objects.
- How: Write pure functions for string manipulation, regex matching, and list processing. Pass the results of these functions to the mutators.
- Rule: A function should either calculate a value or mutate an object (like a `docx.Paragraph`), never both.

### Intermediate Representation (IR)

- Why: Shields business logic from external library complexities (e.g., `docx.oxml` namespaces).
- How: Map external objects to frozen dataclasses (like `FormattedRun`) immediately upon extraction. Perform logic on the dataclass, then map back to the external object.
- Rule: XML namespace calls (`qn('w:r')`) must be strictly confined to dedicated adapter functions or classes.

## 3. Typing & Formatting

### Strong Typing

- Why: Catches integration bugs before runtime and serves as machine-enforceable documentation.
- How: Use Python's typing module (`List`, `Dict`, `Optional`, `Generator`). Run `mypy` in strict mode in your CI pipeline.
- Rule: All function signatures must include parameter and return type hints.

### Linting

- Why: Ensures a uniform visual style and catches cyclomatic complexity automatically.
- How: Use `ruff` as your primary linter and formatter.
- Rule: Enforce a strict line-length limit (e.g., 120 characters) and fail the build on high complexity scores.

## 4. Testing (TDD)

### Test Isolation

- Why: Ensures tests are fast and deterministic.
- How: Inject dependencies. Never call the actual translation LLM or write to physical `.docx` files during unit tests.
- Rule: Pass mock translation managers and in-memory string/IR objects into the functions under test.

### Test States over Exceptions

- Why: `xfail` hides immediate feedback necessary for active development.
- How: Write a failing assertion (Red), implement the code to satisfy it (Green), then clean up the implementation (Refactor).
- Rule: Reserve `xfail` strictly for known bugs deferred to future sprints, never for the active TDD loop.

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

### Current Design Patterns

* **Strategy Pattern (`RuleRegistry`, `FormattingRule`):** Encapsulates specific formatting checks so they can be extended and executed interchangeably without modifying the core translation loops.
* **Iterator Pattern (`_iter_document_elements`):** Uses generators to flatten the complex, nested Word document structure (paragraphs, tables, headers) into a single sequential stream.
* **Factory Pattern (`create_translator`):** Centralizes the configuration and instantiation of the translation models and dependencies.
* **Value Object Pattern (`FormattedRun`):** Uses frozen dataclasses to cleanly represent text formatting, detaching it from the underlying `python-docx` XML objects.

### Recommended Design Patterns

* **Adapter Pattern (`DocxAdapter`):** Wraps all `lxml` namespace (`qn`) calls and `python-docx` specifics in a dedicated adapter class so your business logic never touches raw XML directly.
* **Facade Pattern (`TranslationManager` API):** Hides the complexity of text chunking, caching, find-and-replace, and fallback logic behind a single, clean `translate_text()` interface.
* **Singleton Pattern (Config Loading):** Loads static dictionaries (`preferential_dict`, `table_translations_dict`) exactly once into memory at application start, rather than parsing JSON files per document.

#### Example: DocxAdapter Implementation

```py
import copy
from docx.oxml.ns import qn
from lxml import etree


class DocxAdapter:
    @staticmethod
    def get_xml_element(element, tag_name):
        return element.find(qn(tag_name))
    
    @staticmethod
    def create_xml_element(parent, tag_name, index=None):
        new_elem = etree.SubElement(parent, qn(tag_name))
        if index is not None:
            parent.insert(index, new_elem)
        return new_elem
    
    @staticmethod
    def set_vertical_alignment(run, align_type):
        run_elem = run._element
        rpr = DocxAdapter.get_xml_element(run_elem, 'w:rPr')
        if rpr is None:
            rpr = DocxAdapter.create_xml_element(run_elem, 'w:rPr', index=0)
        
        vert = DocxAdapter.get_xml_element(rpr, 'w:vertAlign')
        if vert is None:
            vert = DocxAdapter.create_xml_element(rpr, 'w:vertAlign')
        
        vert.set(qn('w:val'), align_type)
    
    @staticmethod
    def duplicate_run_with_text(run, new_text):
        new_run_elem = copy.deepcopy(run._element)
        t_elem = DocxAdapter.get_xml_element(new_run_elem, 'w:t')
        
        if t_elem is not None:
            t_elem.text = new_text
            if new_text.startswith(' ') or new_text.endswith(' '):
                t_elem.set(qn('xml:space'), 'preserve')
        
        run._element.addnext(new_run_elem)
        return new_run_elem
    
    @staticmethod
    def extract_and_strip_hyperlinks(paragraph):
        p_elem = paragraph._element
        hyperlinks = list(p_elem.findall(qn('w:hyperlink')))
        data = []
        
        for hl in hyperlinks:
            r_id = hl.get(qn('r:id'))
            url = paragraph.part.rels[r_id].target_ref if r_id and r_id in paragraph.part.rels else ''
            
            text = ""
            for r_elem in hl.findall(qn('w:r')):
                t_elem = DocxAdapter.get_xml_element(r_elem, 'w:t')
                if t_elem is not None and t_elem.text:
                    text += t_elem.text
            
            data.append((text, url))
            
            for r_elem in list(hl.findall(qn('w:r'))):
                p_elem.insert(list(p_elem).index(hl), r_elem)
            p_elem.remove(hl)
        
        return data
```

#### Example 2: `_split_run_for_vertical_align`

the refactored _split_run_for_vertical_align function utilizing the DocxAdapter to cleanly abstract the XML mutations.

```py
class _RunProxy:
    def __init__(self, element):
        self._element = element


def _split_run_for_vertical_align(paragraph, run, text_fragment, align_type, offset=None):
    text = run.text
    idx = offset if offset is not None else text.find(text_fragment)
    if idx == -1:
        return False
    
    before = text[:idx]
    after = text[idx + len(text_fragment):]
    
    if before:
        run.text = before
        new_r_elem = DocxAdapter.duplicate_run_with_text(run, text_fragment)
        DocxAdapter.set_vertical_alignment(_RunProxy(new_r_elem), align_type)
        
        if after:
            DocxAdapter.duplicate_run_with_text(_RunProxy(new_r_elem), after)
    else:
        run.text = text_fragment
        DocxAdapter.set_vertical_alignment(run, align_type)
        
        if after:
            after_r_elem = DocxAdapter.duplicate_run_with_text(run, after)
            after_rPr = DocxAdapter.get_xml_element(after_r_elem, 'w:rPr')
            if after_rPr is not None:
                after_vert = DocxAdapter.get_xml_element(after_rPr, 'w:vertAlign')
                if after_vert is not None:
                    after_rPr.remove(after_vert)
    
    return True
```

#### How to Iject `DocxAdapter` Into Tests

Here is how to mock the DocxAdapter using pytest and unittest.mock to test text formatting without building real lxml document trees.

```py
from unittest.mock import patch, MagicMock


class MockRun:
    def __init__(self, text):
        self.text = text
        self._element = MagicMock()


class MockParagraph:
    def __init__(self, runs):
        self.runs = runs


@patch('scitrans.translate.word_formatting.DocxAdapter')
def test_split_run_for_vertical_align(mock_adapter):
    run = MockRun("Test 1st place")
    paragraph = MockParagraph([run])
    mock_new_run_elem = MagicMock()
    mock_adapter.duplicate_run_with_text.return_value = mock_new_run_elem
    
    result = _split_run_for_vertical_align(paragraph, run, "st", "superscript")
    
    assert result is True
    assert run.text == "Test 1"
    mock_adapter.duplicate_run_with_text.assert_any_call(run, "st")
    mock_adapter.set_vertical_alignment.assert_called()
```

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

import os
import tempfile
import pytest
from docx import Document
from docx.oxml.ns import qn
from scitrans.translate.word_document import translate_word_document
from scitrans.translate.word_formatting import _apply_superscript_ordinals
from scitrans.translate.word_notes import _group_notes_by_paragraph

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'test_formatting_errors_en.docx')


class MockTranslator:
    def __init__(self):
        self.call_count = 0
        self.source_texts = []
    
    def translate_with_best_model(self, text, source_lang, target_lang, use_find_replace, idx, **kwargs):
        self.call_count += 1
        self.source_texts.append(text)
        return {"translated_text": f"[TR:{text}]"}


def _run_translation():
    temp_output = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
    temp_output.close()
    output_path = temp_output.name
    
    mock = MockTranslator()
    
    translate_word_document(
        input_docx_file=FIXTURE_PATH,
        output_docx_file=output_path,
        source_lang='en',
        use_find_replace=False,
        translation_manager=mock
    )
    
    doc = Document(output_path)
    
    # Also collect the notes file if it exists
    notes_path = os.path.splitext(output_path)[0] + '_translation_notes.docx'
    notes_doc = None
    if os.path.exists(notes_path):
        notes_doc = Document(notes_path)
        os.remove(notes_path)
    
    os.remove(output_path)
    
    return doc, mock, notes_doc


# ---------------------------------------------------------------------------
# Header / footer structure tests (expected to fail until code is updated)
# ---------------------------------------------------------------------------

def test_first_page_header_has_tabs():
    doc, _, _ = _run_translation()
    first_page_header = doc.sections[0].first_page_header
    tab_found = False
    for para in first_page_header.paragraphs:
        for run_elem in para._element.findall(qn('w:r')):
            if run_elem.find(qn('w:tab')) is not None:
                tab_found = True
                break
        if tab_found:
            break
    assert tab_found, "First page header should contain tab characters in runs"


def test_other_header_has_left_and_right_text():
    doc, _, _ = _run_translation()
    header = doc.sections[0].header
    
    # The non-first-page header uses a 2-column table for left/right layout.
    # The actual content is in header.tables, not header.paragraphs.
    assert header.tables, "Non-first-page header should contain a table"
    table = header.tables[0]
    row = table.rows[0]
    assert len(row.cells) >= 2, "Header table should have at least 2 columns"
    
    left_text = row.cells[0].text.strip()
    right_text = row.cells[1].text.strip()
    assert left_text, "Left cell of header table should have text"
    assert right_text, "Right cell of header table should have text"
    assert '[TR:' in left_text, f"Left cell should be translated, got: {left_text}"
    assert '[TR:' in right_text, f"Right cell should be translated, got: {right_text}"


def test_first_page_footer_image_tabbed_right():
    doc, _, _ = _run_translation()
    first_page_footer = doc.sections[0].first_page_footer
    
    # The footer should have text on the left and an image tabbed to the right
    has_tab = False
    has_drawing = False
    for para in first_page_footer.paragraphs:
        tabs_in_xml = para._element.findall('.//' + qn('w:tab'))
        if tabs_in_xml:
            has_tab = True
        drawings = para._element.findall('.//' + qn('w:drawing'))
        if drawings:
            has_drawing = True
    
    assert has_tab, "First page footer should have a tab separating text from image"
    assert has_drawing, "First page footer should contain an image/drawing"


def test_first_page_footer_no_page_number():
    doc, _, _ = _run_translation()
    first_page_footer = doc.sections[0].first_page_footer
    
    # The first page footer should NOT contain a page number field
    for para in first_page_footer.paragraphs:
        fld_chars = para._element.findall('.//' + qn('w:fldChar'))
        instr_texts = para._element.findall('.//' + qn('w:instrText'))
        for instr in instr_texts:
            assert 'PAGE' not in (instr.text or '').upper(), \
                "First page footer should not contain a PAGE field code"


def test_page_numbering_is_auto_updating():
    doc, _, _ = _run_translation()
    footer = doc.sections[0].footer
    
    # The regular footer uses a PAGE field for auto-updating page numbers.
    # After translation, this field should be preserved (not replaced with
    # a hard-coded number).
    has_page_field = False
    for para in footer.paragraphs:
        instr_texts = para._element.findall('.//' + qn('w:instrText'))
        for instr in instr_texts:
            if 'PAGE' in (instr.text or '').upper():
                has_page_field = True
                break
    
    assert has_page_field, (
        "Footer should contain a PAGE field code for auto-updating page numbers, "
        "not a hard-coded number"
    )


# ---------------------------------------------------------------------------
# Superscript / formatting note tests (expected to fail until code is updated)
# ---------------------------------------------------------------------------

def test_superscript_footnote_no_formatting_note():
    _, _, notes_doc = _run_translation()
    
    # "footnote1" has a superscript "1" — this should be handled by the
    # superscript rule and NOT produce a formatting note.
    if notes_doc is None:
        return  # No notes at all is fine
    
    all_notes_text = '\n'.join(
        cell.text for table in notes_doc.tables
        for row in table.rows for cell in row.cells
    )
    assert 'footnote' not in all_notes_text.lower(), \
        "Superscript in 'footnote1' should not produce a formatting note"


def test_superscript_ordinals_no_formatting_note():
    _, _, notes_doc = _run_translation()
    
    # "50th" and "75th" have superscript ordinal suffixes — these should be
    # handled by the superscript/subscript rules and NOT produce formatting notes.
    if notes_doc is None:
        return
    
    all_notes_text = '\n'.join(
        cell.text for table in notes_doc.tables
        for row in table.rows for cell in row.cells
    )
    assert '50th' not in all_notes_text and '75th' not in all_notes_text, \
        "Superscript ordinals '50th' and '75th' should not produce formatting notes"


# ---------------------------------------------------------------------------
# Italic / spp. handling tests (expected to fail until code is updated)
# ---------------------------------------------------------------------------

def test_table_cell_0_1_no_formatting_note():
    doc, _, notes_doc = _run_translation()
    table = doc.tables[0]
    cell = table.rows[0].cells[1]
    
    # The cell should have italic text inside brackets (species names)
    has_italic_in_brackets = False
    for para in cell.paragraphs:
        in_bracket = False
        for run in para.runs:
            if '(' in run.text:
                in_bracket = True
            if in_bracket and run.italic and run.text.strip():
                has_italic_in_brackets = True
            if ')' in run.text:
                in_bracket = False
    assert has_italic_in_brackets, (
        "Table cell [0,1] should have italic text inside brackets for species names"
    )
    
    # If the cell is highlighted, there should be a notes row for it
    is_highlighted = any(
        run.font.highlight_color is not None
        for para in cell.paragraphs
        for run in para.runs
        if run.text and run.text.strip()
    )
    if is_highlighted and notes_doc:
        cell_prefix = 'Shrimp remains an important forage species'
        has_row = False
        for notes_table in notes_doc.tables:
            for row in notes_table.rows[1:]:
                if cell_prefix in row.cells[0].text:
                    has_row = True
        assert has_row, (
            "Cell [0,1] is highlighted but has no corresponding row in notes doc"
        )


def test_italic_mismatch_note_uses_check_formatting_key():
    _, _, notes_doc = _run_translation()
    
    # Para 9 has an italic mismatch. The notes should say "check formatting"
    # for the key and should NOT repeat the entire full text of the paragraph.
    if notes_doc is None:
        pytest.fail("Expected a notes document to be generated")
    
    para_9_prefix = 'This bracket mismatch error'
    found = False
    for table in notes_doc.tables:
        for row in table.rows[1:]:
            key_text = row.cells[0].text
            if para_9_prefix in key_text:
                found = True
                assert row.cells[1].text.split('"')[1] == "check formatting"
                break
    
    assert found, "Expected a note for the paragraph with italic mismatch"


def test_final_paragraph_page2_no_formatting_note():
    doc, _, notes_doc = _run_translation()
    
    # Find the final body paragraph that starts with "Shrimp remains..."
    target_para = None
    for para in doc.paragraphs:
        if para.text and 'Shrimp remains' in para.text:
            target_para = para
    assert target_para is not None
    
    # It should NOT be highlighted (italic+spp should be auto-handled)
    is_highlighted = any(
        run.font.highlight_color is not None
        for run in target_para.runs
        if run.text and run.text.strip()
    )
    assert not is_highlighted, (
        "Final paragraph should not be highlighted — italic+spp should be auto-handled"
    )


# ---------------------------------------------------------------------------
# Additional bug-exposing tests
# ---------------------------------------------------------------------------

def test_page_breaks_preserved():
    doc, _, _ = _run_translation()
    page_breaks = []
    for para in doc.paragraphs:
        for br in para._element.findall('.//' + qn('w:br')):
            if br.get(qn('w:type')) == 'page':
                page_breaks.append(br)
    assert len(page_breaks) >= 2, (
        f"Expected at least 2 page breaks, found {len(page_breaks)}"
    )


def test_superscript_ordinals_applied_correctly():
    doc, _, _ = _run_translation()
    # Find the paragraph containing "50th" and "75th"
    target_para = None
    for para in doc.paragraphs:
        if '50' in para.text and '75' in para.text:
            target_para = para
            break
    assert target_para is not None, "Could not find paragraph with 50th/75th"
    
    # Check runs: the suffix after each number should be superscript
    runs = target_para.runs
    found_50_super = False
    found_75_super = False
    for i, run in enumerate(runs):
        if run.text.rstrip().endswith('50') and i + 1 < len(runs):
            next_run = runs[i + 1]
            if next_run.font.superscript and next_run.text.startswith('th'):
                found_50_super = True
        if run.text.rstrip().endswith('75') and i + 1 < len(runs):
            next_run = runs[i + 1]
            if next_run.font.superscript and next_run.text.startswith('th'):
                found_75_super = True
    
    assert found_50_super, "50th should have superscript 'th' suffix"
    assert found_75_super, "75th should have superscript 'th' suffix"


def test_highlighted_paragraphs_match_notes_rows():
    doc, _, notes_doc = _run_translation()
    
    # Count highlighted paragraphs across body + tables
    highlighted_count = 0
    seen_texts = set()
    for para in doc.paragraphs:
        for run in para.runs:
            if run.font.highlight_color is not None and para.text not in seen_texts:
                highlighted_count += 1
                seen_texts.add(para.text)
                break
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        if run.font.highlight_color is not None and para.text not in seen_texts:
                            highlighted_count += 1
                            seen_texts.add(para.text)
                            break
    
    assert notes_doc is not None, "Expected a notes document"
    notes_rows = len(notes_doc.tables[0].rows) - 1  # subtract header row
    
    assert highlighted_count == notes_rows, (
        f"Highlighted paragraphs ({highlighted_count}) should equal "
        f"notes rows ({notes_rows})"
    )


# ---------------------------------------------------------------------------
# Superscript ordinals: French "e" suffix must only superscript after the
# target number, not the first "e" found in the run.
# ---------------------------------------------------------------------------

def test_superscript_ordinals_french_targets_correct_position():
    # Simulates French translation output where "50th" -> "50e" and "75th" -> "75e"
    # The "e" after each number should be superscripted, NOT random "e" chars
    # in surrounding words like "ne", "entraîner", "Cette", etc.
    doc = Document()
    para = doc.add_paragraph(
        "Cette note de bas de page ne doit pas entraîner. Les 50e ou 75e percentiles."
    )
    formatting_records = []
    _apply_superscript_ordinals(para, ['50th', '75th'], formatting_records, 'source')

    # Reconstruct the full text with superscript positions marked
    full_text = ""
    superscripted_positions = []
    for run in para.runs:
        if run.font.superscript:
            for ch in run.text:
                superscripted_positions.append(len(full_text))
                full_text += ch
        else:
            full_text += run.text

    # The only superscripted characters should be the "e" in "50e" and "75e"
    idx_50e = full_text.find("50e")
    idx_75e = full_text.find("75e")
    assert idx_50e != -1, f"Could not find '50e' in reconstructed text: {full_text!r}"
    assert idx_75e != -1, f"Could not find '75e' in reconstructed text: {full_text!r}"

    expected_positions = {idx_50e + 2, idx_75e + 2}  # the "e" after the digits
    actual_positions = set(superscripted_positions)

    assert actual_positions == expected_positions, (
        f"Superscript should only be at positions {expected_positions} "
        f"(the 'e' in '50e' and '75e'), but was at {actual_positions}. "
        f"Text: {full_text!r}"
    )


# ---------------------------------------------------------------------------
# Deduplication: same paragraph with multiple records sharing the same URL
# should collapse to one row (the URL-fragment duplication bug).
# ---------------------------------------------------------------------------

def test_dedup_same_paragraph_same_url_fragments():
    # Simulates the bug where a hyperlink spanning multiple runs creates
    # multiple records with different original_text but the same URL
    records = [
        {'original_text': 'A', 'full_paragraph': 'Miller full text', 'notes': 'https://example.com/doc', 'type': 'hyperlink'},
        {'original_text': 'Near', 'full_paragraph': 'Miller full text', 'notes': 'https://example.com/doc', 'type': 'hyperlink'},
        {'original_text': 'l', 'full_paragraph': 'Miller full text', 'notes': 'https://example.com/doc', 'type': 'hyperlink'},
        {'original_text': 'y Successful', 'full_paragraph': 'Miller full text', 'notes': 'https://example.com/doc', 'type': 'hyperlink'},
    ]
    groups = _group_notes_by_paragraph(records)
    total_rows = sum(len(v) for v in groups.values())
    assert total_rows == 1, (
        f"Same paragraph + same URL should produce 1 row, got {total_rows}"
    )


def test_dedup_same_paragraph_different_errors_kept():
    # Different errors within the same paragraph should each get a row
    records = [
        {'original_text': 'bold text', 'full_paragraph': 'Full paragraph', 'notes': 'bold', 'type': 'formatting'},
        {'original_text': 'italic text', 'full_paragraph': 'Full paragraph', 'notes': 'italic', 'type': 'formatting'},
    ]
    groups = _group_notes_by_paragraph(records)
    total_rows = sum(len(v) for v in groups.values())
    assert total_rows == 2, (
        f"Different errors in same paragraph should produce 2 rows, got {total_rows}"
    )


def test_dedup_different_paragraphs_similar_errors_not_collapsed():
    # Different paragraphs with similar errors should NOT be collapsed
    records = [
        {'original_text': 'text', 'full_paragraph': 'First paragraph text', 'notes': 'italic', 'type': 'formatting'},
        {'original_text': 'text', 'full_paragraph': 'Second paragraph text', 'notes': 'italic', 'type': 'formatting'},
    ]
    groups = _group_notes_by_paragraph(records)
    total_rows = sum(len(v) for v in groups.values())
    assert total_rows == 2, (
        f"Different paragraphs should each get a row even with similar errors, got {total_rows}"
    )


def test_dedup_exact_duplicates_within_paragraph_collapsed():
    # Identical records from the same paragraph should collapse to 1
    records = [
        {'original_text': 'text', 'full_paragraph': 'Same paragraph', 'notes': 'italic', 'type': 'formatting'},
        {'original_text': 'text', 'full_paragraph': 'Same paragraph', 'notes': 'italic', 'type': 'formatting'},
        {'original_text': 'text', 'full_paragraph': 'Same paragraph', 'notes': 'italic', 'type': 'formatting'},
    ]
    groups = _group_notes_by_paragraph(records)
    total_rows = sum(len(v) for v in groups.values())
    assert total_rows == 1, (
        f"Exact duplicate records in same paragraph should collapse to 1, got {total_rows}"
    )

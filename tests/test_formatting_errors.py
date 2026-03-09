import os
import tempfile
import pytest
from docx import Document
from docx.oxml.ns import qn
from scitrans.translate.word_document import translate_word_document


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

    # The fixture has paragraphs with tab characters separating left/right text
    tab_found = False
    for para in first_page_header.paragraphs:
        tabs_in_xml = para._element.findall('.//' + qn('w:tab'))
        if tabs_in_xml:
            tab_found = True
            break
        if '\t' in para.text:
            tab_found = True
            break

    assert tab_found, "First page header should contain tabs separating left and right text"


@pytest.mark.xfail(reason="Other header left/right text not yet implemented")
def test_other_header_has_left_and_right_text():
    doc, _, _ = _run_translation()
    header = doc.sections[0].header

    # The non-first-page header should have left and right aligned text
    # (using a right-aligned tab stop). After translation the header is
    # currently empty — it should contain text on both sides.
    header_text = ''.join(p.text for p in header.paragraphs)
    assert header_text.strip(), "Non-first-page header should have text content"

    # Check that a right-aligned tab stop exists
    has_right_tab = False
    for para in header.paragraphs:
        tabs_elem = para._element.find('.//' + qn('w:tabs'))
        if tabs_elem is not None:
            for tab in tabs_elem.findall(qn('w:tab')):
                if tab.get(qn('w:val')) == 'right':
                    has_right_tab = True
                    break
    assert has_right_tab, "Non-first-page header should have a right-aligned tab stop"


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


@pytest.mark.xfail(reason="Auto-updating page numbering not yet implemented")
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
    _, _, notes_doc = _run_translation()

    # Cell [0,1] of the table has italic species names with "spp." — the
    # italics should be handled by the italic rule and should account for
    # "spp." so no formatting note should be generated for this cell.
    if notes_doc is None:
        return

    # The notes table uses the full paragraph text as the key (column 0).
    # Cell [0,1] content starts with "Shrimp remains..."
    cell_01_prefix = 'Shrimp remains an important forage species'
    for table in notes_doc.tables:
        for row in table.rows[1:]:  # skip header row
            key_text = row.cells[0].text
            if cell_01_prefix in key_text:
                details = row.cells[1].text
                assert 'check formatting' not in details.lower() and \
                       'formatting' not in details.lower(), \
                    f"Table cell [0,1] should not have formatting notes, got: {details}"


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
                details = row.cells[1].text
                # The key in the notes should be short (like "check formatting"),
                # not the entire paragraph text repeated
                assert 'check formatting' in details.lower() or \
                       'italic' in details.lower(), \
                    f"Notes for italic mismatch should mention 'check formatting', got: {details}"
                # The key (column 0) should NOT be the full paragraph text
                # repeated — it should be a reasonable summary
                assert len(key_text) < 200, \
                    f"Notes key should not repeat the entire paragraph text (len={len(key_text)})"
                break

    assert found, "Expected a note for the paragraph with italic mismatch"


def test_final_paragraph_page2_no_formatting_note():
    _, _, notes_doc = _run_translation()

    # The final paragraph of page 2 (para 11) has italic species names with
    # "spp." — the italics should be handled by the italic rule and should
    # NOT produce a formatting note.
    if notes_doc is None:
        return

    para_11_prefix = 'Shrimp remains an important forage species'
    for table in notes_doc.tables:
        for row in table.rows[1:]:
            key_text = row.cells[0].text
            # This paragraph appears both in the table cell and as body text.
            # Check body text version (paragraph, not table cell).
            if para_11_prefix in key_text:
                details = row.cells[1].text
                # If the note mentions bracket mismatch or formatting issues
                # for italics that should have been handled, that's a failure
                if 'bracket' in details.lower() or 'could not be' in details.lower():
                    pytest.fail(
                        f"Final paragraph of page 2 should not have italic formatting "
                        f"notes, got: {details}"
                    )

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
    # FIXME: this is only partially working:
    #  should make sure that there isn't a formatting error that gets highlighted
    #  right now there is no entry in the notes document (which is correct),
    #   BUT, it is highlighted and the formatting has not been performed correctly
    
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
                assert row.cells[1].text.split('"')[1] == "check formatting"
                break
    
    assert found, "Expected a note for the paragraph with italic mismatch"


def test_final_paragraph_page2_no_formatting_note():
    # FIXME: this test isn't working.
    #  it passes, but the paragraph is not correctly handled and the table row is added
    
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

# TODO: write more new new failing tests
"""
- please write failing tests for all of these errors:
  - all of the following new tests are based on the fixture test_formatting_errors_en.docx
    - make sure that the page breaks are not deleted from the fixture
        - maybe we can just test to make sure that the table is on the second page
    - 50th and 75th do not get replaced correctly
      - the first "e" (fr for th) in the run is superscripted (but it should not be),
        and neither "e" that is adjacent to the 50 or 75 are superscripted
    - why is there a different amount of highlighting and notes?
      - there are 4 highlighted paragraphs (1 in the table, 3 others)
        - that needs to lead to 4 rows in the test_formatting docx
        - every highlighted row in the notes doc should have 1 corresponding highlighted paragraph in the translated doc
        - the row writing and highlighting should be handled in the same place to prevent this from being possible
          - please confirm: is there some funny code in the deduplication parts of the codebase that contribute to this error?
- please update current tests to fail:
  - test_final_paragraph_page2_no_formatting_note
    - this isn't working at all
  - test_table_cell_0_1_no_formatting_note is not working correctly either
    - as mentioned above some highlighting is not triggering a row entry. This is the case. cell 0 1 does not have a row entry in the table, but it should because it's highlighted and the italic (incl spp) text did not get italicised correctly
  - tabs/justification are not correct on the header page. they have no tab and none of the text is right justified anymore, but the test still passes
- other notes:
  - i was considering splitting the notes_doc that accompanies the translation doc into 2 tables. one table for formatting issues from sections.tables and another for sections.paragraphs. That could clarify, simplify, etc. and could fix some of these errors.
  - i removed the truncation of key_text because that's not what we were supposed to be doing. the original intent was that if there is an italics error, the "Details" column in the Formatting Notes docx says:
    "check formatting": Italic bracket formatting could not be automatically applied — bracket count mismatch after translation
    - it used to say the whole entire full paragraph again, but that's not useful for this case. it now works as intended and i updated the tests to check for it correctly.

"""

import pytest
from tests.conftest import run_word_translation

FIXTURES = [
    ('test_document_structure_en.docx', 'en'),
    ('test_document_structure_fr.docx', 'fr'),
]


@pytest.fixture(scope="module", params=FIXTURES, ids=[f[1] for f in FIXTURES])
def translated(request):
    fixture_name, source_lang = request.param
    doc, mock, _ = run_word_translation(fixture_name, source_lang)
    return doc, mock


def test_header_paragraph_translated(translated):
    doc, _ = translated
    header = doc.sections[2].header
    assert header.paragraphs, "Section 2 header should have paragraphs"
    assert '[TR:' in header.paragraphs[0].text


def test_footer_paragraphs_translated(translated):
    doc, _ = translated
    for section_idx in [0, 1, 2]:
        footer = doc.sections[section_idx].footer
        assert footer.paragraphs, f"Section {section_idx} footer should have paragraphs"
        assert '[TR:' in footer.paragraphs[0].text, (
            f"Section {section_idx} footer not translated: {footer.paragraphs[0].text}"
        )


def test_header_table_cells_translated(translated):
    doc, _ = translated
    header = doc.sections[0].header
    assert header.tables, "Header should contain a table"
    row = header.tables[0].rows[0]
    assert len(row.cells) >= 2
    
    cell_0_text = row.cells[0].text
    cell_1_text = row.cells[1].text
    assert '[TR:' in cell_0_text, f"Cell 0 should be translated, got: {cell_0_text}"
    # Short cells (< 20 chars) are intentionally left as-is by table cell dispatch
    assert '[TR:' in cell_1_text or len(cell_1_text.strip()) < 20


def test_first_page_header_translated(translated):
    doc, _ = translated
    header = doc.sections[0].first_page_header
    assert header.paragraphs, "First page header should have paragraphs"
    assert '[TR:' in header.paragraphs[0].text


def test_first_page_footer_translated(translated):
    doc, _ = translated
    footer = doc.sections[0].first_page_footer
    assert footer.paragraphs, "First page footer should have paragraphs"
    assert '[TR:' in footer.paragraphs[0].text


def test_even_page_header_translated(translated):
    doc, _ = translated
    header = doc.sections[2].even_page_header
    assert header.paragraphs, "Even page header should have paragraphs"
    assert '[TR:' in header.paragraphs[0].text


def test_linked_header_not_double_translated(translated):
    _, mock = translated
    double_translated = [text for text in mock.source_texts if text.startswith('[TR:')]
    assert len(double_translated) == 0, (
        f"No source texts should start with '[TR:', got: {double_translated[:3]}"
    )


def test_linked_header_skipped(translated):
    doc, _ = translated
    s0_header = doc.sections[0].header
    s1_header = doc.sections[1].header
    
    assert s0_header.tables and s1_header.tables, "Both headers should have tables"
    s0_text = s0_header.tables[0].rows[0].cells[0].text
    s1_text = s1_header.tables[0].rows[0].cells[0].text
    assert s0_text == s1_text and '[TR:' in s0_text


def test_body_paragraphs_still_translated(translated):
    doc, _ = translated
    for para_idx in [0, 2, 4]:
        assert para_idx < len(doc.paragraphs), f"Paragraph {para_idx} does not exist"
        assert '[TR:' in doc.paragraphs[para_idx].text, (
            f"Paragraph {para_idx} not translated: {doc.paragraphs[para_idx].text}"
        )


def test_body_table_still_translated(translated):
    doc, _ = translated
    assert doc.tables, "Document should have tables"
    for row in doc.tables[0].rows:
        for cell in row.cells:
            stripped = cell.text.strip()
            # Short cells (< 20 chars) intentionally left as-is
            if stripped and len(stripped) >= 20:
                assert '[TR:' in cell.text, f"Cell not translated: {cell.text}"

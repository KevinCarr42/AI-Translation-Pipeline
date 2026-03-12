import json
import os
import tempfile

import pytest
from docx import Document
from scitrans.translate.word_document import translate_word_document

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


class MockTranslator:
    def __init__(self):
        self.call_count = 0
        self.source_texts = []
    
    def translate_with_best_model(self, text, source_lang, target_lang, use_find_replace, idx, **kwargs):
        self.call_count += 1
        self.source_texts.append(text)
        return {"translated_text": f"[TR:{text}]"}


@pytest.fixture
def mock_translator():
    return MockTranslator()


@pytest.fixture
def fixture_dir():
    return FIXTURE_DIR


def run_word_translation(fixture_name, source_lang, mock=None):
    fixture_path = os.path.join(FIXTURE_DIR, fixture_name)
    temp = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
    temp.close()
    output_path = temp.name
    
    if mock is None:
        mock = MockTranslator()
    
    translate_word_document(
        input_docx_file=fixture_path,
        output_docx_file=output_path,
        source_lang=source_lang,
        use_find_replace=False,
        translation_manager=mock,
        preserve_json_notes=True
    )
    
    doc = Document(output_path)
    
    notes_base = os.path.splitext(output_path)[0] + '_translation_notes'
    notes_json_path = notes_base + '.json'
    notes_docx_path = notes_base + '.docx'
    notes_data = None
    if os.path.exists(notes_json_path):
        with open(notes_json_path, 'r', encoding='utf-8') as f:
            notes_data = json.load(f)
        os.remove(notes_json_path)
    if os.path.exists(notes_docx_path):
        os.remove(notes_docx_path)
    
    os.remove(output_path)
    return doc, mock, notes_data


def all_notes_text(notes_data):
    if not notes_data:
        return ''
    parts = []
    for section in ['paragraphs', 'tables']:
        for entry in notes_data.get(section, []):
            parts.append(entry.get('full_paragraph', ''))
            for note in entry.get('notes', []):
                parts.append(note.get('original_text', ''))
                parts.append(note.get('detail', ''))
    return '\n'.join(parts)


def notes_entry_count(notes_data):
    if not notes_data:
        return 0
    return len(notes_data.get('paragraphs', [])) + len(notes_data.get('tables', []))

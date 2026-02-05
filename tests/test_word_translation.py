import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from translate.document import translate_word_document
from translate.models import create_translator
from docx import Document
import tempfile


def test_basic_translation():
    print("\n=== Testing basic Word document translation ===\n")
    
    test_cases = [
        {
            'name': 'Valid .docx output created',
            'fixture': os.path.join(os.path.dirname(__file__), 'fixtures', 'test_document.docx'),
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        temp_output = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
        temp_output.close()
        output_path = temp_output.name
        
        try:
            translation_manager = create_translator(
                use_finetuned=False,
                models_to_use=['facebook/mbart-large-50-many-to-many-mmt'],
                use_embedder=False,
                load_models=True
            )
            
            result = translate_word_document(
                input_docx_file=test['fixture'],
                output_docx_file=output_path,
                source_lang="en",
                use_find_replace=False,
                translation_manager=translation_manager
            )
            
            if os.path.exists(output_path):
                doc = Document(output_path)
                if len(doc.paragraphs) > 0:
                    print(f"[PASS] {test['name']}")
                    print(f"  Output: {output_path}")
                    print(f"  Paragraphs: {len(doc.paragraphs)}")
                    passed += 1
                else:
                    print(f"[FAIL] {test['name']}")
                    print(f"  Expected: Valid document with paragraphs")
                    print(f"  Got: Empty document")
                    failed += 1
            else:
                print(f"[FAIL] {test['name']}")
                print(f"  Expected: Output file created")
                print(f"  Got: No output file")
                failed += 1
        
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    print(f"\n{passed} passed, {failed} failed\n")
    assert failed == 0, f"{failed} test cases failed"


def test_bold_preservation():
    print("\n=== Testing bold text preservation ===\n")
    
    test_cases = [
        {
            'name': 'Bold formatting preserved',
            'fixture': os.path.join(os.path.dirname(__file__), 'fixtures', 'test_document.docx'),
            'paragraph_idx': 1,
            'expected_bold_runs': True
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        temp_output = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
        temp_output.close()
        output_path = temp_output.name
        
        try:
            translation_manager = create_translator(
                use_finetuned=False,
                models_to_use=['facebook/mbart-large-50-many-to-many-mmt'],
                use_embedder=False,
                load_models=True
            )
            
            translate_word_document(
                input_docx_file=test['fixture'],
                output_docx_file=output_path,
                source_lang="en",
                use_find_replace=False,
                translation_manager=translation_manager
            )
            
            doc = Document(output_path)
            paragraph = doc.paragraphs[test['paragraph_idx']]
            
            has_bold = any(run.bold for run in paragraph.runs)
            
            if has_bold == test['expected_bold_runs']:
                print(f"[PASS] {test['name']}")
                print(f"  Has bold runs: {has_bold}")
                passed += 1
            else:
                print(f"[FAIL] {test['name']}")
                print(f"  Expected bold runs: {test['expected_bold_runs']}")
                print(f"  Got: {has_bold}")
                print(f"  Run details: {[(r.bold, r.text) for r in paragraph.runs]}")
                failed += 1
        
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    print(f"\n{passed} passed, {failed} failed\n")
    assert failed == 0, f"{failed} test cases failed"


def test_italic_preservation():
    print("\n=== Testing italic text preservation ===\n")
    
    test_cases = [
        {
            'name': 'Italic formatting preserved',
            'fixture': os.path.join(os.path.dirname(__file__), 'fixtures', 'test_document.docx'),
            'paragraph_idx': 2,
            'expected_italic_runs': True
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        temp_output = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
        temp_output.close()
        output_path = temp_output.name
        
        try:
            translation_manager = create_translator(
                use_finetuned=False,
                models_to_use=['facebook/mbart-large-50-many-to-many-mmt'],
                use_embedder=False,
                load_models=True
            )
            
            translate_word_document(
                input_docx_file=test['fixture'],
                output_docx_file=output_path,
                source_lang="en",
                use_find_replace=False,
                translation_manager=translation_manager
            )
            
            doc = Document(output_path)
            paragraph = doc.paragraphs[test['paragraph_idx']]
            
            has_italic = any(run.italic for run in paragraph.runs)
            
            if has_italic == test['expected_italic_runs']:
                print(f"[PASS] {test['name']}")
                print(f"  Has italic runs: {has_italic}")
                passed += 1
            else:
                print(f"[FAIL] {test['name']}")
                print(f"  Expected italic runs: {test['expected_italic_runs']}")
                print(f"  Got: {has_italic}")
                print(f"  Run details: {[(r.italic, r.text) for r in paragraph.runs]}")
                failed += 1
        
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    print(f"\n{passed} passed, {failed} failed\n")
    assert failed == 0, f"{failed} test cases failed"


def test_table_translation():
    print("\n=== Testing table content translation ===\n")
    
    test_cases = [
        {
            'name': 'Table structure preserved',
            'fixture': os.path.join(os.path.dirname(__file__), 'fixtures', 'test_document.docx'),
            'expected_tables': 1,
            'expected_rows': 3,
            'expected_cols': 2
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        temp_output = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
        temp_output.close()
        output_path = temp_output.name
        
        try:
            translation_manager = create_translator(
                use_finetuned=False,
                models_to_use=['facebook/mbart-large-50-many-to-many-mmt'],
                use_embedder=False,
                load_models=True
            )
            
            translate_word_document(
                input_docx_file=test['fixture'],
                output_docx_file=output_path,
                source_lang="en",
                use_find_replace=False,
                translation_manager=translation_manager
            )
            
            doc = Document(output_path)
            
            if len(doc.tables) != test['expected_tables']:
                print(f"[FAIL] {test['name']}")
                print(f"  Expected tables: {test['expected_tables']}")
                print(f"  Got: {len(doc.tables)}")
                failed += 1
                continue
            
            table = doc.tables[0]
            num_rows = len(table.rows)
            num_cols = len(table.rows[0].cells) if table.rows else 0
            
            if num_rows == test['expected_rows'] and num_cols == test['expected_cols']:
                all_cells_have_text = all(
                    cell.text.strip() != ''
                    for row in table.rows
                    for cell in row.cells
                )
                
                if all_cells_have_text:
                    print(f"[PASS] {test['name']}")
                    print(f"  Tables: {len(doc.tables)}, Rows: {num_rows}, Cols: {num_cols}")
                    passed += 1
                else:
                    print(f"[FAIL] {test['name']}")
                    print(f"  Expected: All cells with text")
                    print(f"  Got: Some empty cells")
                    failed += 1
            else:
                print(f"[FAIL] {test['name']}")
                print(f"  Expected rows: {test['expected_rows']}, cols: {test['expected_cols']}")
                print(f"  Got rows: {num_rows}, cols: {num_cols}")
                failed += 1
        
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    print(f"\n{passed} passed, {failed} failed\n")
    assert failed == 0, f"{failed} test cases failed"


def test_empty_runs_skipped():
    print("\n=== Testing empty runs skipped without error ===\n")
    
    test_cases = [
        {
            'name': 'Empty paragraphs handled without error',
            'fixture': os.path.join(os.path.dirname(__file__), 'fixtures', 'test_document.docx'),
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        temp_output = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
        temp_output.close()
        output_path = temp_output.name
        
        try:
            translation_manager = create_translator(
                use_finetuned=False,
                models_to_use=['facebook/mbart-large-50-many-to-many-mmt'],
                use_embedder=False,
                load_models=True
            )
            
            result = translate_word_document(
                input_docx_file=test['fixture'],
                output_docx_file=output_path,
                source_lang="en",
                use_find_replace=False,
                translation_manager=translation_manager
            )
            
            doc = Document(output_path)
            original_doc = Document(test['fixture'])
            
            if len(doc.paragraphs) == len(original_doc.paragraphs):
                print(f"[PASS] {test['name']}")
                print(f"  Paragraphs preserved: {len(doc.paragraphs)}")
                passed += 1
            else:
                print(f"[FAIL] {test['name']}")
                print(f"  Expected paragraphs: {len(original_doc.paragraphs)}")
                print(f"  Got: {len(doc.paragraphs)}")
                failed += 1
        
        except Exception as e:
            print(f"[FAIL] {test['name']}")
            print(f"  Exception: {str(e)}")
            failed += 1
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
    
    print(f"\n{passed} passed, {failed} failed\n")
    assert failed == 0, f"{failed} test cases failed"


def test_output_path_generation():
    print("\n=== Testing automatic output path generation ===\n")
    
    test_cases = [
        {
            'name': 'Output file auto-named when not specified',
            'fixture': os.path.join(os.path.dirname(__file__), 'fixtures', 'test_document.docx'),
            'expected_pattern': '_translated_'
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        try:
            translation_manager = create_translator(
                use_finetuned=False,
                models_to_use=['facebook/mbart-large-50-many-to-many-mmt'],
                use_embedder=False,
                load_models=True
            )
            
            result = translate_word_document(
                input_docx_file=test['fixture'],
                output_docx_file=None,
                source_lang="en",
                use_find_replace=False,
                translation_manager=translation_manager
            )
            
            if test['expected_pattern'] in result and os.path.exists(result):
                print(f"[PASS] {test['name']}")
                print(f"  Generated path: {result}")
                passed += 1
                os.remove(result)
            else:
                print(f"[FAIL] {test['name']}")
                print(f"  Expected pattern in path: {test['expected_pattern']}")
                print(f"  Got: {result}")
                print(f"  Exists: {os.path.exists(result)}")
                failed += 1
                if os.path.exists(result):
                    os.remove(result)
        
        except Exception as e:
            print(f"[FAIL] {test['name']}")
            print(f"  Exception: {str(e)}")
            failed += 1
    
    print(f"\n{passed} passed, {failed} failed\n")
    assert failed == 0, f"{failed} test cases failed"

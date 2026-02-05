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


def test_spacing_between_runs():
    print("\n=== Testing spacing preserved between runs ===\n")
    
    test_cases = [
        {
            'name': 'Paragraph with multiple formatted runs preserves spacing',
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
                models_to_use=['mbart_large_50'],
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
            
            translated_doc = Document(output_path)
            
            has_spacing_issue = False
            problematic_text = None
            for paragraph in translated_doc.paragraphs:
                if len(paragraph.runs) > 1:
                    text = paragraph.text
                    if '[NOVALIDTRANSLATIONS]' in text or '[TRANSLATION FAILED]' in text:
                        continue
                    
                    words = text.split()
                    for word in words:
                        if len(word) > 25:
                            has_spacing_issue = True
                            problematic_text = text
                            print(f"  Found suspicious long word: {word[:50]}")
                            print(f"  Full paragraph text: {text[:100]}")
                            break
                    if has_spacing_issue:
                        break
            
            if not has_spacing_issue:
                print(f"[PASS] {test['name']}")
                print(f"  No spacing issues detected in multi-run paragraphs")
                passed += 1
            else:
                print(f"[FAIL] {test['name']}")
                print(f"  Spacing issues detected between runs")
                if problematic_text:
                    print(f"  Problem text: {problematic_text[:150]}")
                failed += 1
            
            os.remove(output_path)
        
        except Exception as e:
            print(f"[FAIL] {test['name']}")
            print(f"  Exception: {str(e)}")
            failed += 1
            if os.path.exists(output_path):
                os.remove(output_path)
    
    print(f"\n{passed} passed, {failed} failed\n")
    assert failed == 0, f"{failed} test cases failed"


def test_mid_paragraph_formatting():
    print("\n=== Testing mid-paragraph formatting preservation ===\n")
    
    passed = 0
    failed = 0
    
    temp_input = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
    temp_input.close()
    input_path = temp_input.name
    
    temp_output = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
    temp_output.close()
    output_path = temp_output.name
    
    try:
        # Create a document with mid-paragraph bold text
        doc = Document()
        para = doc.add_paragraph()
        run1 = para.add_run("This is ")
        run2 = para.add_run("bold")
        run2.bold = True
        run3 = para.add_run(" text in the middle.")
        doc.save(input_path)
        
        # Verify the input has the expected format
        input_doc = Document(input_path)
        input_para = input_doc.paragraphs[0]
        input_bold_runs = [r for r in input_para.runs if r.bold and r.text.strip()]
        
        print(f"  Input paragraph runs: {[(r.text, r.bold) for r in input_para.runs]}")
        print(f"  Input bold runs count: {len(input_bold_runs)}")
        
        translation_manager = create_translator(
            use_finetuned=False,
            models_to_use=['facebook/mbart-large-50-many-to-many-mmt'],
            use_embedder=False,
            load_models=True
        )
        
        translate_word_document(
            input_docx_file=input_path,
            output_docx_file=output_path,
            source_lang="en",
            use_find_replace=False,
            translation_manager=translation_manager
        )
        
        # Check output preserves bold formatting
        output_doc = Document(output_path)
        output_para = output_doc.paragraphs[0]
        output_bold_runs = [r for r in output_para.runs if r.bold and r.text.strip()]
        
        print(f"  Output paragraph runs: {[(r.text, r.bold) for r in output_para.runs]}")
        print(f"  Output bold runs count: {len(output_bold_runs)}")
        
        # The output should have at least one bold run (the middle segment)
        if len(output_bold_runs) >= 1:
            print(f"[PASS] Mid-paragraph bold formatting preserved")
            print(f"  Bold text preserved: '{output_bold_runs[0].text}'")
            passed += 1
        else:
            print(f"[FAIL] Mid-paragraph bold formatting lost")
            print(f"  Expected: At least 1 bold run")
            print(f"  Got: {len(output_bold_runs)} bold runs")
            failed += 1
    
    except Exception as e:
        print(f"[FAIL] Exception during test: {str(e)}")
        import traceback
        traceback.print_exc()
        failed += 1
    
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
    
    print(f"\n{passed} passed, {failed} failed\n")
    assert failed == 0, f"{failed} test cases failed"

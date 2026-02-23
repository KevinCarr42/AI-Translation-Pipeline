import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from translate.document import translate_word_document, _has_formatting_differences, _translate_paragraph, _get_all_runs, _join_run_texts, _split_into_sentences, _set_proofing_language, HyperlinkRunWrapper
from translate.models import create_translator
from docx import Document
from docx.shared import RGBColor
from docx.enum.text import WD_COLOR_INDEX
import tempfile
import re
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
import docx.oxml.ns as ns


def test_basic_translation():
    print("\n=== Testing basic Word document translation ===\n")
    
    test_cases = [
        {
            'name': 'Valid .docx output created',
            'fixture': os.path.join(os.path.dirname(__file__), 'fixtures', 'test_document_formatting_en.docx'),
            'source_lang': 'en',
        },
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
                source_lang=test['source_lang'],
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
            'fixture': os.path.join(os.path.dirname(__file__), 'fixtures', 'test_document_formatting_en.docx'),
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
            'fixture': os.path.join(os.path.dirname(__file__), 'fixtures', 'test_document_formatting_en.docx'),
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
            'fixture': os.path.join(os.path.dirname(__file__), 'fixtures', 'test_document_formatting_en.docx'),
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
            'fixture': os.path.join(os.path.dirname(__file__), 'fixtures', 'test_document_formatting_en.docx'),
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
            'fixture': os.path.join(os.path.dirname(__file__), 'fixtures', 'test_document_formatting_en.docx'),
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
            'fixture': os.path.join(os.path.dirname(__file__), 'fixtures', 'test_document_formatting_en.docx'),
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
    
    class MockTranslationManager:
        def translate_with_best_model(self, text, source_lang, target_lang,
                                      use_find_replace, idx, use_cache=True):
            return {"translated_text": "TRANSLATED: " + text}
    
    mock_manager = MockTranslationManager()
    
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
        
        translate_word_document(
            input_docx_file=input_path,
            output_docx_file=output_path,
            source_lang="en",
            use_find_replace=False,
            translation_manager=mock_manager
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


def test_color_normalization():
    print("\n=== Testing explicit black vs inherited color normalization ===\n")
    
    passed = 0
    failed = 0
    
    doc = Document()
    para = doc.add_paragraph()
    run1 = para.add_run("Explicit black ")
    run1.font.color.rgb = RGBColor(0, 0, 0)
    run2 = para.add_run("inherited color")
    
    has_diff = _has_formatting_differences(para)
    
    if not has_diff:
        print("[PASS] Explicit black and inherited color treated as identical")
        passed += 1
    else:
        print("[FAIL] Explicit black and inherited color treated as different")
        print(f"  Expected: False (no formatting differences)")
        print(f"  Got: {has_diff}")
        failed += 1
    
    print(f"\n{passed} passed, {failed} failed\n")
    assert failed == 0, f"{failed} test cases failed"


def test_long_paragraph_chunking():
    print("\n=== Testing long paragraph chunking (>600 chars) ===\n")
    
    passed = 0
    failed = 0
    
    class MockTranslationManager:
        def translate_with_best_model(self, text, source_lang, target_lang,
                                      use_find_replace, idx, use_cache=True):
            return {"translated_text": "TRANSLATED: " + text}
    
    mock_manager = MockTranslationManager()
    
    # Build a paragraph with >600 chars of text across a single run
    long_text = "This is a test sentence. " * 30  # ~750 chars
    doc = Document()
    para = doc.add_paragraph()
    para.add_run(long_text.strip())
    
    original_length = len(long_text.strip())
    
    _translate_paragraph(para, mock_manager, "en", "fr", False, 1)
    
    output_text = para.text
    # The mock prefixes each chunk with "TRANSLATED: " so output should be longer than original
    if len(output_text) >= original_length:
        print(f"[PASS] Long paragraph not truncated")
        print(f"  Input length: {original_length}")
        print(f"  Output length: {len(output_text)}")
        passed += 1
    else:
        print(f"[FAIL] Long paragraph appears truncated")
        print(f"  Input length: {original_length}")
        print(f"  Output length: {len(output_text)}")
        print(f"  Output: {output_text[:200]}...")
        failed += 1
    
    print(f"\n{passed} passed, {failed} failed\n")
    assert failed == 0, f"{failed} test cases failed"


def _add_hyperlink(paragraph, url, link_text):
    part = paragraph.part
    r_id = part.relate_to(url, RT.HYPERLINK, is_external=True)
    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(ns.qn('r:id'), r_id)
    new_run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    rStyle = OxmlElement('w:rStyle')
    rStyle.set(ns.qn('w:val'), 'Hyperlink')
    rPr.append(rStyle)
    new_run.append(rPr)
    t = OxmlElement('w:t')
    t.set(ns.qn('xml:space'), 'preserve')
    t.text = link_text
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._element.append(hyperlink)


def _get_full_paragraph_text(paragraph):
    nsmap = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    text_parts = []
    for child in paragraph._element:
        if child.tag == ns.qn('w:r'):
            for t in child.findall('.//w:t', nsmap):
                if t.text:
                    text_parts.append(t.text)
        elif child.tag == ns.qn('w:hyperlink'):
            for t in child.findall('.//w:t', nsmap):
                if t.text:
                    text_parts.append(t.text)
    return ''.join(text_parts)


def _paragraph_has_hyperlink_relationship(paragraph):
    nsmap = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    hyperlinks = paragraph._element.findall('.//w:hyperlink', nsmap)
    return len(hyperlinks) > 0


def test_hyperlink_in_paragraph():
    print("\n=== Testing hyperlink text preserved in correct position after translation ===\n")
    
    passed = 0
    failed = 0
    
    class MockTranslationManager:
        def translate_with_best_model(self, text, source_lang, target_lang,
                                      use_find_replace, idx, use_cache=True):
            return {"translated_text": "TRANSLATED: " + text}
    
    mock_manager = MockTranslationManager()
    
    test_cases = [
        {
            'name': 'Hyperlink at START of sentence',
            'build': lambda doc: _build_para_link_start(doc),
            'expected_link_text': 'Our Website',
        },
        {
            'name': 'Hyperlink in MIDDLE of sentence',
            'build': lambda doc: _build_para_link_middle(doc),
            'expected_link_text': 'DFO Science',
        },
        {
            'name': 'Hyperlink at END of sentence',
            'build': lambda doc: _build_para_link_end(doc),
            'expected_link_text': 'the official page',
        },
    ]
    
    for test in test_cases:
        temp_input = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
        temp_input.close()
        input_path = temp_input.name
        
        temp_output = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
        temp_output.close()
        output_path = temp_output.name
        
        try:
            doc = Document()
            test['build'](doc)
            doc.save(input_path)
            
            # Verify input was built correctly
            input_doc = Document(input_path)
            input_para = input_doc.paragraphs[0]
            input_full_text = _get_full_paragraph_text(input_para)
            print(f"  [{test['name']}] Input full text: {input_full_text}")
            print(f"  [{test['name']}] Input paragraph.text: {input_para.text}")
            print(f"  [{test['name']}] Input runs (paragraph.runs): {[r.text for r in input_para.runs]}")
            
            translate_word_document(
                input_docx_file=input_path,
                output_docx_file=output_path,
                source_lang="en",
                use_find_replace=False,
                translation_manager=mock_manager
            )
            
            output_doc = Document(output_path)
            output_para = output_doc.paragraphs[0]
            output_full_text = _get_full_paragraph_text(output_para)
            
            print(f"  [{test['name']}] Output full text (including hyperlink XML): {output_full_text}")
            print(f"  [{test['name']}] Output paragraph.text: {output_para.text}")
            
            link_text = test['expected_link_text']
            case_failed = False
            
            # Check 1: hyperlink text must appear within the full paragraph text
            if link_text not in output_full_text:
                print(f"[FAIL] {test['name']} - hyperlink text '{link_text}' missing from output entirely")
                case_failed = True
            
            # Check 2: the translated content should include the hyperlink text as part of
            # the translated sentence, not as an orphan. The mock prepends "TRANSLATED: "
            # so we should see both the translated marker and the link text.
            if not case_failed:
                has_translated_content = 'TRANSLATED:' in output_full_text
                if not has_translated_content:
                    print(f"[FAIL] {test['name']} - no translated content found in output")
                    print(f"  Output: {output_full_text}")
                    case_failed = True
            
            # Check 3: hyperlink text must NOT be stranded after sentence-ending punctuation.
            # The bug causes output like "TRANSLATED: Visit for details.Our Website"
            if not case_failed:
                orphan_pattern = re.compile(r'[.!?]' + re.escape(link_text) + r'$')
                if orphan_pattern.search(output_full_text.rstrip()):
                    print(f"[FAIL] {test['name']} - hyperlink text orphaned after sentence-ending punctuation")
                    print(f"  Output: {output_full_text}")
                    case_failed = True
            
            # Check 4: hyperlink XML should be stripped after translation
            if not case_failed:
                has_hyperlink = _paragraph_has_hyperlink_relationship(output_para)
                if has_hyperlink:
                    print(f"[FAIL] {test['name']} - hyperlink XML was not stripped after translation")
                    case_failed = True
            
            # Check 5: the hyperlink text should have been included in what was sent to
            # the translator. Since mock returns "TRANSLATED: <input>", we can verify the
            # link text was part of the input by checking if it appears after "TRANSLATED: "
            if not case_failed:
                translated_marker_idx = output_full_text.find('TRANSLATED: ')
                if translated_marker_idx >= 0:
                    translated_portion = output_full_text[translated_marker_idx:]
                    if link_text not in translated_portion:
                        print(f"[FAIL] {test['name']} - hyperlink text was not included in translation input")
                        print(f"  Translated portion: {translated_portion}")
                        print(f"  Expected to contain: {link_text}")
                        case_failed = True
            
            if case_failed:
                failed += 1
            else:
                print(f"[PASS] {test['name']}")
                passed += 1
        
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)
    
    print(f"\n{passed} passed, {failed} failed\n")
    assert failed == 0, f"{failed} test cases failed"


def _build_para_link_start(doc):
    para = doc.add_paragraph()
    _add_hyperlink(para, 'https://example.com', 'Our Website')
    run_after = para.add_run(' has more details about the project.')
    return para


def _build_para_link_middle(doc):
    para = doc.add_paragraph()
    para.add_run('Publications will be posted on ')
    _add_hyperlink(para, 'https://dfo-mpo.gc.ca', 'DFO Science')
    run_after = para.add_run(' as they become available.')
    return para


def _build_para_link_end(doc):
    para = doc.add_paragraph()
    para.add_run('For more information visit ')
    _add_hyperlink(para, 'https://example.com/info', 'the official page')
    return para


def test_get_all_runs():
    print("\n=== Testing _get_all_runs() returns hyperlink runs in document order ===\n")

    passed = 0
    failed = 0

    # Test 1: mixed paragraph with plain run, hyperlink, plain run
    doc = Document()
    para = doc.add_paragraph()
    para.add_run('Before ')
    _add_hyperlink(para, 'https://example.com', 'Link Text')
    para.add_run(' after.')

    all_runs = _get_all_runs(para)
    texts = [(r.text, is_hl) for r, is_hl in all_runs]
    expected = [('Before ', False), ('Link Text', True), (' after.', False)]

    if texts == expected:
        print(f"[PASS] Document order correct: {texts}")
        passed += 1
    else:
        print(f"[FAIL] Document order wrong")
        print(f"  Expected: {expected}")
        print(f"  Got: {texts}")
        failed += 1

    # Test 2: hyperlink wrapper is correct type
    hyperlink_entries = [(r, is_hl) for r, is_hl in all_runs if is_hl]
    if len(hyperlink_entries) == 1 and isinstance(hyperlink_entries[0][0], HyperlinkRunWrapper):
        print(f"[PASS] Hyperlink run is HyperlinkRunWrapper instance")
        passed += 1
    else:
        print(f"[FAIL] Hyperlink run type wrong")
        failed += 1

    # Test 3: mutating wrapper.text changes the underlying XML
    wrapper = hyperlink_entries[0][0]
    wrapper.text = 'Modified'
    nsmap = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    hyperlinks = para._element.findall(ns.qn('w:hyperlink'))
    xml_text = hyperlinks[0].findall('.//w:t', nsmap)[0].text

    if xml_text == 'Modified':
        print(f"[PASS] Wrapper .text setter mutates underlying XML")
        passed += 1
    else:
        print(f"[FAIL] Wrapper .text setter did not mutate XML")
        print(f"  Expected: 'Modified'")
        print(f"  Got: '{xml_text}'")
        failed += 1

    # Test 4: paragraph with no hyperlinks returns same as paragraph.runs
    doc2 = Document()
    para2 = doc2.add_paragraph()
    para2.add_run('Plain text only.')
    all_runs2 = _get_all_runs(para2)

    if len(all_runs2) == 1 and all_runs2[0][1] is False and all_runs2[0][0].text == 'Plain text only.':
        print(f"[PASS] Plain paragraph returns runs with is_hyperlink=False")
        passed += 1
    else:
        print(f"[FAIL] Plain paragraph result unexpected: {[(r.text, hl) for r, hl in all_runs2]}")
        failed += 1

    print(f"\n{passed} passed, {failed} failed\n")
    assert failed == 0, f"{failed} test cases failed"


def test_join_run_texts():
    print("\n=== Testing _join_run_texts boundary spacing ===\n")

    passed = 0
    failed = 0

    class FakeRun:
        def __init__(self, text):
            self.text = text

    def make_runs(texts):
        return [(FakeRun(t), False) for t in texts]

    def make_mixed_runs(entries):
        return [(FakeRun(t), is_hl) for t, is_hl in entries]

    # Test 1: same-type runs with no whitespace — NO space inserted (Word mid-word splits)
    result = _join_run_texts(make_runs(['N', 'ewfoundland']))
    if result == 'Newfoundland':
        print("[PASS] Same-type runs joined without space (mid-word split)")
        passed += 1
    else:
        print(f"[FAIL] Expected 'Newfoundland', got '{result}'")
        failed += 1

    # Test 2: same-type runs with existing whitespace preserved
    result = _join_run_texts(make_runs(['Region ', 'du']))
    if result == 'Region du':
        print("[PASS] Existing whitespace preserved between same-type runs")
        passed += 1
    else:
        print(f"[FAIL] Expected 'Region du', got '{result}'")
        failed += 1

    # Test 3: hyperlink boundary — space inserted when no whitespace
    result = _join_run_texts(make_mixed_runs([('Visit', False), ('Link', True)]))
    if result == 'Visit Link':
        print("[PASS] Space inserted at hyperlink boundary")
        passed += 1
    else:
        print(f"[FAIL] Expected 'Visit Link', got '{result}'")
        failed += 1

    # Test 4: hyperlink boundary — no double space when whitespace exists
    result = _join_run_texts(make_mixed_runs([('Visit ', False), ('Link', True)]))
    if result == 'Visit Link':
        print("[PASS] No double space at hyperlink boundary with existing whitespace")
        passed += 1
    else:
        print(f"[FAIL] Expected 'Visit Link', got '{result}'")
        failed += 1

    # Test 5: single run — no change
    result = _join_run_texts(make_runs(['Hello world']))
    if result == 'Hello world':
        print("[PASS] Single run unchanged")
        passed += 1
    else:
        print(f"[FAIL] Expected 'Hello world', got '{result}'")
        failed += 1

    # Test 6: empty text runs between same-type — no spaces injected
    result = _join_run_texts(make_runs(['Hello', '', 'world']))
    if result == 'Helloworld':
        print("[PASS] Same-type empty runs joined without space")
        passed += 1
    else:
        print(f"[FAIL] Expected 'Helloworld', got '{result}'")
        failed += 1

    # Test 7: None text runs
    result = _join_run_texts([(FakeRun(None), False), (FakeRun('text'), False)])
    if result == 'text':
        print("[PASS] None text runs handled correctly")
        passed += 1
    else:
        print(f"[FAIL] Expected 'text', got '{result}'")
        failed += 1

    # Test 8: empty list
    result = _join_run_texts([])
    if result == '':
        print("[PASS] Empty list returns empty string")
        passed += 1
    else:
        print(f"[FAIL] Expected '', got '{result}'")
        failed += 1

    print(f"\n{passed} passed, {failed} failed\n")
    assert failed == 0, f"{failed} test cases failed"


def test_split_into_sentences():
    print("\n=== Testing _split_into_sentences ===\n")

    passed = 0
    failed = 0

    test_cases = [
        {
            'name': 'Figure label not split',
            'input': 'Figure 1. Map showing the area.',
            'expected': ['Figure 1. Map showing the area.'],
        },
        {
            'name': 'Fig abbreviation protected, normal boundary works',
            'input': 'Fig. 3 shows results. The data is clear.',
            'expected': ['Fig. 3 shows results.', 'The data is clear.'],
        },
        {
            'name': 'French Tableau label not split',
            'input': 'Tableau 2. Les résultats montrent que...',
            'expected': ['Tableau 2. Les résultats montrent que...'],
        },
        {
            'name': 'Table label protected, normal boundary works',
            'input': 'Table 1. First sentence. Second sentence.',
            'expected': ['Table 1. First sentence.', 'Second sentence.'],
        },
        {
            'name': 'Normal sentence splitting still works',
            'input': 'Hello world. Goodbye world.',
            'expected': ['Hello world.', 'Goodbye world.'],
        },
        {
            'name': 'No split points returns single item',
            'input': 'No periods here',
            'expected': ['No periods here'],
        },
    ]

    for test in test_cases:
        result = _split_into_sentences(test['input'])
        if result == test['expected']:
            print(f"[PASS] {test['name']}")
            passed += 1
        else:
            print(f"[FAIL] {test['name']}")
            print(f"  Expected: {test['expected']}")
            print(f"  Got:      {result}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed\n")
    assert failed == 0, f"{failed} test cases failed"


def test_hyperlink_stripping_and_records():
    print("\n=== Testing hyperlink stripping, cyan highlighting, and records collection ===\n")

    passed = 0
    failed = 0

    class MockTranslationManager:
        def translate_with_best_model(self, text, source_lang, target_lang,
                                      use_find_replace, idx, use_cache=True):
            return {"translated_text": "TRANSLATED: " + text}

    mock_manager = MockTranslationManager()

    # --- Test: paragraph WITH hyperlink ---
    temp_file = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
    temp_file.close()
    temp_path = temp_file.name

    try:
        doc = Document()
        para = doc.add_paragraph()
        para.add_run('Visit ')
        _add_hyperlink(para, 'https://example.com', 'our site')
        para.add_run(' for details.')
        doc.save(temp_path)

        # Re-open so relationship IDs are properly persisted
        doc = Document(temp_path)
        para = doc.paragraphs[0]

        hyperlink_records = []
        _translate_paragraph(para, mock_manager, 'en', 'fr', False, 1, hyperlink_records=hyperlink_records)

        # Check 1: no w:hyperlink elements remain
        hyperlinks_remaining = para._element.findall(ns.qn('w:hyperlink'))
        if len(hyperlinks_remaining) == 0:
            print("[PASS] Hyperlink XML stripped from paragraph")
            passed += 1
        else:
            print(f"[FAIL] Hyperlink XML not stripped — {len(hyperlinks_remaining)} w:hyperlink elements remain")
            failed += 1

        # Check 2: cyan highlighting applied to all runs
        all_runs_after = _get_all_runs(para)
        all_have_cyan = all(
            run.font.highlight_color == WD_COLOR_INDEX.TURQUOISE
            for run, _ in all_runs_after
            if run.text and run.text.strip()
        )
        if all_have_cyan:
            print("[PASS] Cyan (turquoise) highlighting applied to all runs")
            passed += 1
        else:
            highlight_values = [(run.text, run.font.highlight_color) for run, _ in all_runs_after]
            print(f"[FAIL] Not all runs have cyan highlighting: {highlight_values}")
            failed += 1

        # Check 3: hyperlink_records populated correctly
        if len(hyperlink_records) == 1:
            record = hyperlink_records[0]
            record_ok = True

            if record['original_text'] != 'our site':
                print(f"[FAIL] Record original_text wrong: '{record['original_text']}'")
                record_ok = False

            if record['url'] != 'https://example.com':
                print(f"[FAIL] Record url wrong: '{record['url']}'")
                record_ok = False

            if 'Visit' not in record['full_sentence'] or 'our site' not in record['full_sentence']:
                print(f"[FAIL] Record full_sentence missing expected text: '{record['full_sentence']}'")
                record_ok = False

            if record_ok:
                print(f"[PASS] hyperlink_records populated correctly: {record}")
                passed += 1
            else:
                failed += 1
        else:
            print(f"[FAIL] Expected 1 hyperlink record, got {len(hyperlink_records)}")
            failed += 1

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    # --- Test: paragraph WITHOUT hyperlink should NOT get cyan highlighting ---
    try:
        doc2 = Document()
        para2 = doc2.add_paragraph()
        para2.add_run('Plain text without any links.')

        hyperlink_records_plain = []
        _translate_paragraph(para2, mock_manager, 'en', 'fr', False, 1, hyperlink_records=hyperlink_records_plain)

        all_runs_plain = _get_all_runs(para2)
        any_cyan = any(
            hasattr(run, 'font') and hasattr(run.font, 'highlight_color') and run.font.highlight_color == WD_COLOR_INDEX.TURQUOISE
            for run, _ in all_runs_plain
        )
        if not any_cyan:
            print("[PASS] No cyan highlighting on paragraph without hyperlinks")
            passed += 1
        else:
            print("[FAIL] Cyan highlighting incorrectly applied to paragraph without hyperlinks")
            failed += 1

    except Exception as e:
        print(f"[FAIL] Exception in no-hyperlink test: {e}")
        failed += 1

    print(f"\n{passed} passed, {failed} failed\n")
    assert failed == 0, f"{failed} test cases failed"


def test_write_hyperlink_notes():
    print("\n=== Testing write_hyperlink_notes creates valid notes document ===\n")

    from translate.hyperlink_notes import write_hyperlink_notes

    passed = 0
    failed = 0

    records = [
        {'original_text': 'Example Link', 'full_sentence': 'Visit Example Link for details.', 'url': 'https://example.com'},
        {'original_text': 'Another', 'full_sentence': 'See Another for more.', 'url': 'https://another.com'},
    ]

    temp_file = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
    temp_file.close()
    temp_path = temp_file.name

    try:
        write_hyperlink_notes(records, temp_path)

        doc = Document(temp_path)

        # Check 1: document has at least one table
        if len(doc.tables) >= 1:
            print("[PASS] Document contains at least one table")
            passed += 1
        else:
            print(f"[FAIL] Expected at least 1 table, got {len(doc.tables)}")
            failed += 1

        table = doc.tables[0]

        # Check 2: table has 3 columns
        num_cols = len(table.rows[0].cells) if table.rows else 0
        if num_cols == 3:
            print("[PASS] Table has 3 columns")
            passed += 1
        else:
            print(f"[FAIL] Expected 3 columns, got {num_cols}")
            failed += 1

        # Check 3: table has 3 rows (1 header + 2 data)
        num_rows = len(table.rows)
        if num_rows == 3:
            print("[PASS] Table has 3 rows (1 header + 2 data)")
            passed += 1
        else:
            print(f"[FAIL] Expected 3 rows, got {num_rows}")
            failed += 1

        # Check 4: header row contains correct labels
        header_texts = [cell.text for cell in table.rows[0].cells]
        expected_headers = ['Original Text', 'Full Sentence', 'URL']
        if header_texts == expected_headers:
            print(f"[PASS] Header row correct: {header_texts}")
            passed += 1
        else:
            print(f"[FAIL] Header row wrong")
            print(f"  Expected: {expected_headers}")
            print(f"  Got: {header_texts}")
            failed += 1

        # Check 5: first data row contains correct values
        first_row_texts = [cell.text for cell in table.rows[1].cells]
        expected_first_row = ['Example Link', 'Visit Example Link for details.', 'https://example.com']
        if first_row_texts == expected_first_row:
            print(f"[PASS] First data row correct: {first_row_texts}")
            passed += 1
        else:
            print(f"[FAIL] First data row wrong")
            print(f"  Expected: {expected_first_row}")
            print(f"  Got: {first_row_texts}")
            failed += 1

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    print(f"\n{passed} passed, {failed} failed\n")
    assert failed == 0, f"{failed} test cases failed"


def test_proofing_language_set():
    print("\n=== Testing proofing language set on translated documents ===\n")

    passed = 0
    failed = 0

    class MockTranslationManager:
        def translate_with_best_model(self, text, source_lang, target_lang,
                                      use_find_replace, idx, use_cache=True):
            return {"translated_text": "TRANSLATED: " + text}

    mock_manager = MockTranslationManager()

    test_cases = [
        {
            'name': 'English to French sets fr-CA',
            'source_lang': 'en',
            'expected_locale': 'fr-CA',
        },
        {
            'name': 'French to English sets en-CA',
            'source_lang': 'fr',
            'expected_locale': 'en-CA',
        },
    ]

    for test in test_cases:
        temp_input = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
        temp_input.close()
        input_path = temp_input.name

        temp_output = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
        temp_output.close()
        output_path = temp_output.name

        try:
            doc = Document()
            doc.add_paragraph("This is a test sentence.")
            doc.save(input_path)

            translate_word_document(
                input_docx_file=input_path,
                output_docx_file=output_path,
                source_lang=test['source_lang'],
                use_find_replace=False,
                translation_manager=mock_manager
            )

            output_doc = Document(output_path)
            all_r_elements = list(output_doc.element.iter(ns.qn('w:r')))

            if not all_r_elements:
                print(f"[FAIL] {test['name']} - no w:r elements found in output")
                failed += 1
                continue

            all_correct = True
            for r_elem in all_r_elements:
                rPr = r_elem.find(ns.qn('w:rPr'))
                if rPr is None:
                    print(f"[FAIL] {test['name']} - w:r element missing rPr")
                    all_correct = False
                    break
                lang = rPr.find(ns.qn('w:lang'))
                if lang is None:
                    print(f"[FAIL] {test['name']} - rPr missing w:lang element")
                    all_correct = False
                    break
                val = lang.get(ns.qn('w:val'))
                if val != test['expected_locale']:
                    print(f"[FAIL] {test['name']} - expected w:val='{test['expected_locale']}', got '{val}'")
                    all_correct = False
                    break

            if all_correct:
                print(f"[PASS] {test['name']} - all {len(all_r_elements)} runs have w:lang w:val='{test['expected_locale']}'")
                passed += 1
            else:
                failed += 1

        finally:
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)

    print(f"\n{passed} passed, {failed} failed\n")
    assert failed == 0, f"{failed} test cases failed"

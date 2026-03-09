import os
from scitrans.translate.word_document import translate_word_document, _translate_paragraph, write_translations_notes
from scitrans.translate.utils import split_by_sentences
from scitrans.translate.models import create_translator
from docx import Document
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
            
            translate_word_document(
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
            
            notes_path = os.path.splitext(result)[0] + '_translation_notes.docx'
            if os.path.exists(notes_path):
                os.remove(notes_path)
        
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


def test_long_paragraph_chunking():
    print("\n=== Testing long paragraph chunking (>600 chars) ===\n")
    
    passed = 0
    failed = 0
    
    class MockTranslationManager:
        def translate_with_best_model(self, text, source_lang, target_lang,
                                      use_find_replace, idx, use_cache=True, preferential_dict=None):
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
                                      use_find_replace, idx, use_cache=True, preferential_dict=None):
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


def test_split_by_sentences():
    print("\n=== Testing split_by_sentences ===\n")
    
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
        result, _ = split_by_sentences(test['input'])
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
                                      use_find_replace, idx, use_cache=True, preferential_dict=None):
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
        
        formatting_records = []
        _translate_paragraph(para, mock_manager, 'en', 'fr', False, 1, formatting_records=formatting_records)
        
        # Check 1: no w:hyperlink elements remain
        hyperlinks_remaining = para._element.findall(ns.qn('w:hyperlink'))
        if len(hyperlinks_remaining) == 0:
            print("[PASS] Hyperlink XML stripped from paragraph")
            passed += 1
        else:
            print(f"[FAIL] Hyperlink XML not stripped — {len(hyperlinks_remaining)} w:hyperlink elements remain")
            failed += 1
        
        # Check 2: formatting_records contains a hyperlink record
        hyperlink_records = [r for r in formatting_records if 'https://' in r.get('notes', '')]
        if len(hyperlink_records) >= 1:
            record = hyperlink_records[0]
            record_ok = True
            
            if record['original_text'] != 'our site':
                print(f"[FAIL] Record original_text wrong: '{record['original_text']}'")
                record_ok = False
            
            if record['notes'] != 'https://example.com':
                print(f"[FAIL] Record notes wrong: '{record['notes']}'")
                record_ok = False
            
            if 'Visit' not in record['full_sentence'] or 'our site' not in record['full_sentence']:
                print(f"[FAIL] Record full_sentence missing expected text: '{record['full_sentence']}'")
                record_ok = False
            
            if record_ok:
                print(f"[PASS] formatting_records populated correctly: {record}")
                passed += 1
            else:
                failed += 1
        else:
            print(f"[FAIL] Expected at least 1 hyperlink record, got {len(hyperlink_records)}")
            for record in formatting_records:
                print(record)
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
        _translate_paragraph(para2, mock_manager, 'en', 'fr', False, 1, formatting_records=hyperlink_records_plain)
        
        all_runs_plain = list(para2.runs)
        any_cyan = any(
            hasattr(run, 'font') and hasattr(run.font, 'highlight_color') and run.font.highlight_color == WD_COLOR_INDEX.TURQUOISE
            for run in all_runs_plain
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


def test_write_formatting_notes():
    print("\n=== Testing write_translations_notes creates valid notes document ===\n")
    
    passed = 0
    failed = 0
    
    records = [
        {'original_text': 'Example Link', 'full_sentence': 'Visit Example Link for details.', 'notes': 'https://example.com'},
        {'original_text': 'Another', 'full_sentence': 'See Another for more.', 'notes': 'https://another.com'},
    ]
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
    temp_file.close()
    temp_path = temp_file.name
    
    try:
        write_translations_notes(records, temp_path)
        
        doc = Document(temp_path)
        
        # Check 1: document has at least one table
        if len(doc.tables) >= 1:
            print("[PASS] Document contains at least one table")
            passed += 1
        else:
            print(f"[FAIL] Expected at least 1 table, got {len(doc.tables)}")
            failed += 1
        
        table = doc.tables[0]
        
        # Check 2: table has 2 columns (new format)
        num_cols = len(table.rows[0].cells) if table.rows else 0
        if num_cols == 2:
            print("[PASS] Table has 2 columns")
            passed += 1
        else:
            print(f"[FAIL] Expected 2 columns, got {num_cols}")
            failed += 1
        
        # Check 3: table has 3 rows (1 header + 2 data, grouped by full_sentence)
        num_rows = len(table.rows)
        if num_rows == 3:
            print(f"[PASS] Table has {num_rows} rows (1 header + 2 data)")
            passed += 1
        else:
            print(f"[FAIL] Expected 3 rows, got {num_rows}")
            failed += 1
        
        # Check 4: header row has correct labels
        header_texts = [cell.text for cell in table.rows[0].cells]
        if header_texts[0] == 'Full Paragraph (source language)' and header_texts[1] == 'Details':
            print(f"[PASS] Header row correct: {header_texts}")
            passed += 1
        else:
            print(f"[FAIL] Header row wrong: {header_texts}")
            failed += 1
        
        # Check 5: first data row contains the full sentence and details
        first_row_texts = [cell.text for cell in table.rows[1].cells]
        if 'Visit Example Link for details.' in first_row_texts[0]:
            print(f"[PASS] First data row paragraph text correct")
            passed += 1
        else:
            print(f"[FAIL] First data row paragraph text wrong: {first_row_texts[0]}")
            failed += 1
        
        if 'Example Link' in first_row_texts[1] and 'https://example.com' in first_row_texts[1]:
            print(f"[PASS] First data row details correct")
            passed += 1
        else:
            print(f"[FAIL] First data row details wrong: {first_row_texts[1]}")
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
                                      use_find_replace, idx, use_cache=True, preferential_dict=None):
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

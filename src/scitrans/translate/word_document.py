import json
import os
import re
from datetime import datetime

from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.ns import qn
from lxml import etree
from scitrans import config
from scitrans.rules_based_replacements.token_utils import get_translation_value
from scitrans.translate.models import create_translator
from scitrans.translate.utils import split_into_chunks, normalize_apostrophes
from scitrans.translate.word_formatting import apply_formatting_rules, is_numeric, convert_numeric
from scitrans.translate.word_formatting import parse_formatted_string


# TODO: refactor notes into one module (hyperlinks, formats, etc)
def write_hyperlink_notes(hyperlink_records, output_path):
    document = Document()
    document.add_heading('Hyperlink Translation Notes', level=1)
    
    table = document.add_table(rows=1, cols=3)
    table.style = 'Table Grid'
    
    header_cells = table.rows[0].cells
    header_cells[0].text = 'Original Text'
    header_cells[1].text = 'Full Sentence'
    header_cells[2].text = 'URL'  # FIXME for other notes
    
    for record in hyperlink_records:
        row_cells = table.add_row().cells
        row_cells[0].text = record['original_text']
        row_cells[1].text = record['full_sentence']
        row_cells[2].text = record['url']
    
    document.save(output_path)


def _get_all_runs(paragraph):
    return list(paragraph.runs)


def _join_run_texts(all_runs):
    return ''.join(run.text or '' for run in all_runs)


def _get_run_format_key(run):
    font_color = None
    if run.font.color and run.font.color.rgb:
        font_color = str(run.font.color.rgb)
    if font_color == '000000':
        font_color = None
    
    return (
        run.bold,
        run.italic,
        run.underline,
        run.font.name,
        run.font.size,
        font_color
    )


def _merge_identical_runs(paragraph):
    # FIXME: this should ignore colour
    #  everything should just use default colour
    #  making a note when the colour deviates
    #  ignore_colour=True flag?
    #  bypass entirely, always merge, note if there are formatting changes in Notes table docx
    all_runs = _get_all_runs(paragraph)
    if len(all_runs) <= 1:
        return
    
    run_info = []
    for run in all_runs:
        if run.text:
            run_info.append((run, _get_run_format_key(run)))
    
    if len(run_info) <= 1:
        return
    
    i = 0
    while i < len(run_info) - 1:
        current_run, current_key = run_info[i]
        next_run, next_key = run_info[i + 1]
        
        if current_key == next_key:
            current_run.text += next_run.text
            next_run.text = ''
            run_info.pop(i + 1)
        else:
            i += 1


def _build_format_segments(paragraph):
    segments = []
    current_segment_runs = []
    current_format_key = None
    
    for run in _get_all_runs(paragraph):
        if not run.text:
            continue
        
        format_key = _get_run_format_key(run)
        
        if current_format_key is None:
            current_format_key = format_key
            current_segment_runs = [run]
        elif format_key == current_format_key:
            current_segment_runs.append(run)
        else:
            if current_segment_runs:
                segments.append(current_segment_runs)
            current_format_key = format_key
            current_segment_runs = [run]
    
    if current_segment_runs:
        segments.append(current_segment_runs)
    
    return segments


def _has_formatting_differences(paragraph):
    format_keys = set()
    for run in _get_all_runs(paragraph):
        if run.text and run.text.strip():
            format_keys.add(_get_run_format_key(run))
            if len(format_keys) > 1:
                return True
    return False


def _distribute_text_to_runs(translated_text, content_runs, original_lengths):
    total_original = sum(original_lengths)
    split_points = []
    cumulative = 0
    for length in original_lengths[:-1]:
        cumulative += length
        ratio = cumulative / total_original
        raw_offset = int(ratio * len(translated_text))
        # Walk forward to nearest space, then fall back to walking backward
        forward = raw_offset
        while forward < len(translated_text) and translated_text[forward] != ' ':
            forward += 1
        backward = raw_offset
        while backward > 0 and translated_text[backward] != ' ':
            backward -= 1
        if forward < len(translated_text):
            boundary = forward
        else:
            boundary = backward
        split_points.append(boundary)
    
    pieces = []
    previous = 0
    for point in split_points:
        pieces.append(translated_text[previous:point])
        previous = point
    pieces.append(translated_text[previous:])
    # Only strip the outer edges, not internal boundaries
    if pieces:
        pieces[0] = pieces[0].lstrip()
        pieces[-1] = pieces[-1].rstrip()
    
    # Fall back if any content run would be left empty while others have text
    non_empty_pieces = [p for p in pieces if p]
    if len(non_empty_pieces) < len(content_runs) and len(non_empty_pieces) > 0:
        pieces = [translated_text] + [''] * (len(content_runs) - 1)
    
    for run, piece in zip(content_runs, pieces):
        run.text = piece


def _chunk_and_translate(
        text,
        translation_manager,
        source_lang,
        target_lang,
        use_find_replace,
        idx,
        use_cache=True,
        preferential_dict=None,
        chunk_by="sentences"
):
    chunks, _ = split_into_chunks(text, chunk_by)
    
    translated_parts = []
    for chunk in chunks:
        result = translation_manager.translate_with_best_model(
            text=chunk,
            source_lang=source_lang,
            target_lang=target_lang,
            use_find_replace=use_find_replace,
            idx=idx,
            use_cache=use_cache,
            preferential_dict=preferential_dict
        )
        translated_parts.append(result.get("translated_text", "[TRANSLATION FAILED]"))
    return ' '.join(translated_parts)


def _translate_paragraph(
        paragraph,
        translation_manager,
        source_lang,
        target_lang,
        use_find_replace,
        idx,
        use_cache=True,
        hyperlink_records=None,
        preferential_dict=None,
        chunk_by="sentences"
):
    _apply_cyan = False
    p_elem = paragraph._element
    hyperlink_elems = p_elem.findall(qn('w:hyperlink'))
    has_hyperlinks = len(hyperlink_elems) > 0
    
    if hyperlink_records is not None and has_hyperlinks:
        wns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
        # Build full paragraph text for context (including hyperlink run text)
        all_text_parts = []
        for child in p_elem:
            if child.tag == qn('w:r'):
                t_elem = child.find(f'{{{wns}}}t')
                if t_elem is not None and t_elem.text:
                    all_text_parts.append(t_elem.text)
            elif child.tag == qn('w:hyperlink'):
                for r_elem in child.findall(f'{{{wns}}}r'):
                    t_elem = r_elem.find(f'{{{wns}}}t')
                    if t_elem is not None and t_elem.text:
                        all_text_parts.append(t_elem.text)
        full_paragraph_text = ''.join(all_text_parts)
        
        # Collect hyperlink records before stripping
        for hl_elem in hyperlink_elems:
            r_id = hl_elem.get(qn('r:id'))
            if r_id and r_id in paragraph.part.rels:
                url = paragraph.part.rels[r_id].target_ref
            else:
                url = ''
            for r_elem in hl_elem.findall(f'{{{wns}}}r'):
                t_elem = r_elem.find(f'{{{wns}}}t')
                original_text = t_elem.text if t_elem is not None and t_elem.text else ''
                hyperlink_records.append({
                    'original_text': original_text,
                    'full_sentence': full_paragraph_text,
                    'url': url,
                })
        
        # Strip hyperlink XML wrappers — move w:r elements up into w:p
        for hl_elem in list(p_elem.findall(qn('w:hyperlink'))):
            for r_elem in list(hl_elem.findall(qn('w:r'))):
                p_elem.insert(list(p_elem).index(hl_elem), r_elem)
            p_elem.remove(hl_elem)
        
        _apply_cyan = True
    
    all_runs = _get_all_runs(paragraph)
    if not all_runs:
        return idx
    
    full_text = _join_run_texts(all_runs)
    
    if not full_text.strip():
        return idx
    
    # Clean up invisible run boundaries by merging identical adjacent runs
    _merge_identical_runs(paragraph)
    
    # Re-fetch after merge since runs may have changed
    all_runs = _get_all_runs(paragraph)
    
    # Check if paragraph has actual formatting differences
    if not _has_formatting_differences(paragraph):
        # No formatting differences - translate as single unit (original simple approach)
        leading_ws = ''
        trailing_ws = ''
        text_to_translate = full_text
        
        if text_to_translate and text_to_translate[0].isspace():
            i = 0
            while i < len(text_to_translate) and text_to_translate[i].isspace():
                i += 1
            leading_ws = text_to_translate[:i]
            text_to_translate = text_to_translate[i:]
        
        if text_to_translate and text_to_translate[-1].isspace():
            i = len(text_to_translate) - 1
            while i >= 0 and text_to_translate[i].isspace():
                i -= 1
            trailing_ws = text_to_translate[i + 1:]
            text_to_translate = text_to_translate[:i + 1]
        
        if not text_to_translate:
            return idx
        
        translated_text = _chunk_and_translate(
            text_to_translate,
            translation_manager,
            source_lang,
            target_lang,
            use_find_replace,
            idx,
            use_cache,
            preferential_dict=preferential_dict,
            chunk_by=chunk_by
        )
        translated_text = normalize_apostrophes(translated_text)
        
        first_content_run = None
        for run in all_runs:
            if run.text and run.text.strip():
                first_content_run = run
                break
        
        if first_content_run:
            first_content_run.text = leading_ws + translated_text + trailing_ws
            found_first = False
            for run in all_runs:
                if run.text and run.text.strip():
                    if found_first:
                        run.text = ''
                    else:
                        found_first = True
    
    else:
        # Has formatting differences - translate as single unit and remap proportionally
        content_runs = [run for run in all_runs if run.text and run.text.strip()]
        full_text = _join_run_texts(all_runs)
        original_lengths = [len(run.text) for run in content_runs]
        
        text_to_translate = full_text.strip()
        if not text_to_translate:
            return idx
        
        translated_text = _chunk_and_translate(
            text_to_translate,
            translation_manager,
            source_lang,
            target_lang,
            use_find_replace,
            idx,
            use_cache,
            preferential_dict=preferential_dict,
            chunk_by=chunk_by
        )
        translated_text = normalize_apostrophes(translated_text)
        
        rule_fired, formatted_runs = apply_formatting_rules(full_text, translated_text, all_runs)
        
        if rule_fired and formatted_runs:
            # Clear all existing run text, then assign from FormattedRun list
            for run in all_runs:
                run.text = ''
            for i, fmt_run in enumerate(formatted_runs):
                if i < len(content_runs):
                    content_runs[i].text = fmt_run.text
                    content_runs[i].italic = fmt_run.italic
                    if fmt_run.superscript:
                        content_runs[i].font.superscript = True
                    if fmt_run.subscript:
                        content_runs[i].font.subscript = True
                else:
                    # More formatted runs than content runs — append to last run
                    content_runs[-1].text += fmt_run.text
        else:
            _distribute_text_to_runs(translated_text, content_runs, original_lengths)
    
    if _apply_cyan:
        
        for run in _get_all_runs(paragraph):
            if hasattr(run, 'font') and hasattr(run.font, 'highlight_color'):
                run.font.highlight_color = WD_COLOR_INDEX.TURQUOISE
    
    return idx + 1


def _translate_table_cell(
        cell,
        translation_manager,
        source_lang,
        target_lang,
        use_find_replace,
        idx,
        use_cache=True,
        hyperlink_records=None,
        preferential_dict=None,
        table_translations_dict=None,
        chunk_by="sentences"
):
    to_fr = target_lang == "fr"
    cell_text = cell.text
    
    if not cell_text or not cell_text.strip():
        return idx
    
    stripped = cell_text.strip()
    
    # 1. Numeric conversion
    if config.NUMERIC_CONVERSION_CONFIG.get("enabled") and is_numeric(stripped):
        converted = convert_numeric(stripped, to_fr=to_fr)
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                if run.text.strip():
                    run.text = converted
                    converted = ""
        return idx
    
    # 2. Exact match in table translations dict
    if table_translations_dict and stripped in table_translations_dict:
        
        raw_replacement = table_translations_dict[stripped]
        formatted_runs = parse_formatted_string(raw_replacement)
        content_runs = [run for p in cell.paragraphs for run in p.runs if run.text.strip()]
        for run in cell.paragraphs[0].runs:
            run.text = ''
        for i, fmt_run in enumerate(formatted_runs):
            if i < len(content_runs):
                content_runs[i].text = fmt_run.text
                content_runs[i].italic = fmt_run.italic
                if fmt_run.superscript:
                    content_runs[i].font.superscript = True
                if fmt_run.subscript:
                    content_runs[i].font.subscript = True
            else:
                content_runs[-1].text += fmt_run.text
        return idx
    
    # 3. Preferential translations exact match
    if preferential_dict:
        lookup_key = stripped.lower()
        pref_translations = preferential_dict.get("translations", preferential_dict)
        for category, terms in pref_translations.items():
            for term_key, term_data in terms.items():
                if term_key.lower() == lookup_key:
                    if source_lang == "en":
                        
                        match_translation = get_translation_value(term_data)
                    else:
                        match_translation = term_key if source_lang == "fr" else None
                    if match_translation:
                        # Preserve leading capitalization
                        if stripped[0].isupper() and match_translation[0].islower():
                            match_translation = match_translation[0].upper() + match_translation[1:]
                        for paragraph in cell.paragraphs:
                            for run in paragraph.runs:
                                if run.text.strip():
                                    run.text = match_translation
                                    match_translation = ""
                        return idx
    
    # 4. AI translation for cells exceeding minimum length
    min_length = config.TABLE_TRANSLATION_CONFIG.get("min_cell_length_for_ai", 20)
    if len(stripped) >= min_length:
        for paragraph in cell.paragraphs:
            idx = _translate_paragraph(
                paragraph,
                translation_manager,
                source_lang,
                target_lang,
                use_find_replace,
                idx,
                use_cache=use_cache,
                hyperlink_records=hyperlink_records,
                preferential_dict=preferential_dict,
                chunk_by=chunk_by
            )
        return idx
    
    # 5. Short text - leave as-is
    return idx


def _set_proofing_language(document, target_lang):
    locale_map = {'fr': 'fr-CA', 'en': 'en-CA'}
    locale_code = locale_map[target_lang]
    
    for r_elem in document.element.iter(qn('w:r')):
        rPr = r_elem.find(qn('w:rPr'))
        if rPr is None:
            rPr = etree.SubElement(r_elem, qn('w:rPr'))
            r_elem.insert(0, rPr)
        lang = rPr.find(qn('w:lang'))
        if lang is None:
            lang = etree.SubElement(rPr, qn('w:lang'))
        lang.set(qn('w:val'), locale_code)


def translate_word_document(
        input_docx_file,
        output_docx_file=None,
        source_lang="en",
        models_to_use=None,
        use_find_replace=True,
        use_finetuned=True,
        translation_manager=None,
        include_timestamp=True,
        use_cache=True,
        chunk_by="sentences"
):
    if not output_docx_file:
        base, ext = os.path.splitext(input_docx_file)
        date_str = datetime.now().strftime("%Y%m%d")
        if include_timestamp:
            output_docx_file = f"{base}_translated_{date_str}.docx"
        else:
            output_docx_file = f"{base}_translated.docx"
    
    if source_lang not in ["en", "fr"]:
        raise ValueError('source_lang must be either "fr" or "en"')
    
    target_lang = "fr" if source_lang == "en" else "en"
    
    if not translation_manager:
        translation_manager = create_translator(
            use_finetuned=use_finetuned,
            models_to_use=models_to_use,
            use_embedder=True,
            load_models=True
        )
    
    document = Document(input_docx_file)
    idx = 1
    hyperlink_records = []
    
    preferential_dict = None
    if os.path.exists(config.PREFERENTIAL_JSON_PATH):
        with open(config.PREFERENTIAL_JSON_PATH, 'r', encoding='utf-8') as f:
            preferential_dict = json.load(f)
    
    table_translations_dict = None
    if os.path.exists(config.TABLE_TRANSLATIONS_JSON_PATH):
        
        with open(config.TABLE_TRANSLATIONS_JSON_PATH, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        source_key = source_lang
        target_key = target_lang
        if isinstance(raw, list):
            table_translations_dict = {}
            for entry in raw:
                if source_key not in entry or target_key not in entry:
                    continue
                # Strip formatting notation: /text/ -> text, _{text} -> text, ^{text} -> text
                plain_key = re.sub(r'/([^/]+)/', r'\1', entry[source_key])
                plain_key = re.sub(r'[_^]\{([^}]*)\}', r'\1', plain_key)
                if plain_key not in table_translations_dict:
                    table_translations_dict[plain_key] = entry[target_key]
        else:
            table_translations_dict = raw
    
    for paragraph in document.paragraphs:
        idx = _translate_paragraph(
            paragraph,
            translation_manager,
            source_lang,
            target_lang,
            use_find_replace,
            idx,
            use_cache=use_cache,
            hyperlink_records=hyperlink_records,
            preferential_dict=preferential_dict,
            chunk_by=chunk_by
        )
    
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                idx = _translate_table_cell(
                    cell,
                    translation_manager,
                    source_lang,
                    target_lang,
                    use_find_replace,
                    idx,
                    use_cache=use_cache,
                    hyperlink_records=hyperlink_records,
                    preferential_dict=preferential_dict,
                    table_translations_dict=table_translations_dict,
                    chunk_by=chunk_by
                )
    
    translated_hf_ids = set()
    
    header_footer_attrs = [
        'header', 'footer',
        'first_page_header', 'first_page_footer',
        'even_page_header', 'even_page_footer',
    ]
    
    for section in document.sections:
        for attr in header_footer_attrs:
            hf = getattr(section, attr)
            if id(hf._element) in translated_hf_ids:
                continue
            if hf.is_linked_to_previous:
                continue
            translated_hf_ids.add(id(hf._element))
            for paragraph in hf.paragraphs:
                idx = _translate_paragraph(
                    paragraph,
                    translation_manager,
                    source_lang,
                    target_lang,
                    use_find_replace,
                    idx,
                    use_cache=use_cache,
                    hyperlink_records=hyperlink_records,
                    preferential_dict=preferential_dict,
                    chunk_by=chunk_by
                )
            for table in hf.tables:
                for row in table.rows:
                    for cell in row.cells:
                        idx = _translate_table_cell(
                            cell,
                            translation_manager,
                            source_lang,
                            target_lang,
                            use_find_replace,
                            idx,
                            use_cache=use_cache,
                            hyperlink_records=hyperlink_records,
                            preferential_dict=preferential_dict,
                            table_translations_dict=table_translations_dict,
                            chunk_by=chunk_by
                        )
    
    _set_proofing_language(document, target_lang)
    document.save(output_docx_file)
    
    if hyperlink_records:
        notes_path = os.path.splitext(output_docx_file)[0] + '_translation_notes.docx'
        write_hyperlink_notes(hyperlink_records, notes_path)
    
    return output_docx_file

import json
import os
import re
from datetime import datetime

from copy import deepcopy

from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.ns import qn
from lxml import etree
from scitrans import config
from scitrans.rules_based_replacements.token_utils import get_translation_value
from scitrans.translate.models import create_translator
from scitrans.translate.utils import split_into_chunks, reassemble_sentences, reassemble_paragraphs, normalize_apostrophes
from scitrans.translate.word_formatting import apply_formatting_rules, is_numeric, convert_numeric, parse_formatted_string, FormattedRun, detect_patterns
from scitrans.translate.word_notes import add_formatting_notes, has_hyperlinks, write_translations_notes


_MC_NS = 'http://schemas.openxmlformats.org/markup-compatibility/2006'


def _has_shape(elem):
    return (elem.find(qn('w:drawing')) is not None or
            elem.find(qn('w:pict')) is not None or
            elem.find('{%s}AlternateContent' % _MC_NS) is not None)


def _extract_non_run_elements(paragraph):
    p_elem = paragraph._element
    saved = []
    for child in list(p_elem):
        tag = child.tag
        if tag == qn('w:pPr'):
            continue
        # Save non-run elements AND shape-containing runs
        if tag != qn('w:r') or _has_shape(child):
            saved.append(deepcopy(child))
            p_elem.remove(child)
    return saved


def _reinsert_non_run_elements(paragraph, saved):
    p_elem = paragraph._element
    for elem in saved:
        p_elem.append(elem)


def _collapse_runs_preserving_shapes(paragraph):
    p_elem = paragraph._element
    children = list(p_elem)

    run_tag = qn('w:r')

    merged_text = []
    run_group = []

    def _flush_group():
        if not run_group:
            return
        first_run = run_group[0]
        combined = "".join(merged_text)
        for r in run_group[1:]:
            p_elem.remove(r)
        # Rebuild first run with w:t and w:br elements for line breaks
        for old_t in first_run.findall(qn('w:t')):
            first_run.remove(old_t)
        for old_br in first_run.findall(qn('w:br')):
            first_run.remove(old_br)
        parts = re.split(r'([\n\x0c])', combined)
        for piece in parts:
            if piece == '\n':
                etree.SubElement(first_run, qn('w:br'))
            elif piece == '\x0c':
                br = etree.SubElement(first_run, qn('w:br'))
                br.set(qn('w:type'), 'page')
            else:
                tab_parts = piece.split('\t')
                for k, tab_part in enumerate(tab_parts):
                    if k > 0:
                        etree.SubElement(first_run, qn('w:tab'))
                    if tab_part:
                        t = etree.SubElement(first_run, qn('w:t'))
                        t.text = tab_part
                        if tab_part[0] == ' ' or tab_part[-1] == ' ':
                            t.set(qn('xml:space'), 'preserve')

    in_field = 0
    for child in children:
        if child.tag != run_tag:
            _flush_group()
            run_group.clear()
            merged_text.clear()
            continue

        # Skip runs that are part of a field code (PAGE numbers, etc.)
        fld_char = child.find(qn('w:fldChar'))
        if fld_char is not None:
            fld_type = fld_char.get(qn('w:fldCharType'))
            if fld_type == 'begin':
                _flush_group()
                run_group.clear()
                merged_text.clear()
                in_field += 1
            elif fld_type == 'end':
                in_field -= 1
            continue
        if in_field > 0:
            continue

        if _has_shape(child):
            _flush_group()
            run_group.clear()
            merged_text.clear()
            continue

        # Collect text including line breaks from w:br elements
        run_text_parts = []
        for sub in child:
            if sub.tag == qn('w:t'):
                run_text_parts.append(sub.text or '')
            elif sub.tag == qn('w:br'):
                if sub.get(qn('w:type')) == 'page':
                    run_text_parts.append('\x0c')
                else:
                    run_text_parts.append('\n')
            elif sub.tag == qn('w:tab'):
                run_text_parts.append('\t')
        run_text = ''.join(run_text_parts)
        run_group.append(child)
        merged_text.append(run_text)

    _flush_group()


def _has_only_field_runs(paragraph):
    p_elem = paragraph._element
    in_field = 0
    has_any_run = False
    for child in p_elem:
        if child.tag != qn('w:r'):
            continue
        has_any_run = True
        fld_char = child.find(qn('w:fldChar'))
        if fld_char is not None:
            fld_type = fld_char.get(qn('w:fldCharType'))
            if fld_type == 'begin':
                in_field += 1
            elif fld_type == 'end':
                in_field -= 1
            continue
        if in_field > 0:
            continue
        # Found a run outside any field — paragraph has regular content
        t_elem = child.find(qn('w:t'))
        if t_elem is not None and (t_elem.text or '').strip():
            return False
    return has_any_run


def _has_formatting_differences(paragraph):
    for run in list(paragraph.runs):
        if FormattedRun.create(run).has_formatting:
            return True
    return False


def _convert_newlines_to_breaks(paragraph):
    for run in list(paragraph.runs):
        if '\n' not in run.text:
            continue
        run_elem = run._element
        text = run.text
        for old_t in run_elem.findall(qn('w:t')):
            run_elem.remove(old_t)
        for old_br in run_elem.findall(qn('w:br')):
            run_elem.remove(old_br)
        parts = text.split('\n')
        for i, part in enumerate(parts):
            if i > 0:
                etree.SubElement(run_elem, qn('w:br'))
            if part:
                t = etree.SubElement(run_elem, qn('w:t'))
                t.text = part
                if part[0] == ' ' or part[-1] == ' ':
                    t.set(qn('xml:space'), 'preserve')


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
    chunks, chunk_metadata = split_into_chunks(text, chunk_by)
    
    translated_chunks = []
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
        translated_chunks.append(result.get("translated_text", "[TRANSLATION FAILED]"))
    
    if chunk_by == "paragraphs":
        return reassemble_paragraphs(translated_chunks, chunk_metadata)
    else:
        return reassemble_sentences(translated_chunks, chunk_metadata)


def _translate_paragraph(
        paragraph,
        translation_manager,
        source_lang,
        target_lang,
        use_find_replace,
        idx,
        use_cache=True,
        formatting_records=None,
        preferential_dict=None,
        chunk_by="sentences"
):
    has_hl = has_hyperlinks(paragraph, formatting_records)
    detected_patterns = detect_patterns(paragraph)

    has_fmt = _has_formatting_differences(paragraph)
    records_before = len(formatting_records) if formatting_records is not None else 0
    if has_fmt:
        add_formatting_notes(paragraph, formatting_records, detected_patterns)

    _collapse_runs_preserving_shapes(paragraph)

    if _has_only_field_runs(paragraph):
        return idx

    source_text = paragraph.text
    if not source_text:
        return idx

    saved_elements = _extract_non_run_elements(paragraph)

    translated_text = _chunk_and_translate(
        source_text,
        translation_manager,
        source_lang,
        target_lang,
        use_find_replace,
        idx,
        use_cache,
        preferential_dict=preferential_dict,
        chunk_by=chunk_by
    )
    paragraph.text = normalize_apostrophes(translated_text)

    _reinsert_non_run_elements(paragraph, saved_elements)

    apply_formatting_rules(paragraph, detected_patterns, formatting_records, source_text)

    has_fmt_notes = (len(formatting_records) if formatting_records is not None else 0) > records_before

    # Highlight runs in the translated document
    if has_hl or has_fmt_notes:
        color = WD_COLOR_INDEX.TURQUOISE
        if has_fmt_notes and not has_hl:
            color = WD_COLOR_INDEX.YELLOW
        elif has_fmt_notes and has_hl:
            color = WD_COLOR_INDEX.BRIGHT_GREEN
        for run in paragraph.runs:
            if run.text and run.text.strip():
                run.font.highlight_color = color

    _convert_newlines_to_breaks(paragraph)

    return idx + 1


def _apply_numeric_conversion(cell, stripped, to_fr):
    converted = convert_numeric(stripped, to_fr=to_fr)
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            if run.text.strip():
                run.text = converted
                converted = ""


def _apply_table_dict_replacement(cell, stripped, table_translations_dict):
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


def _find_preferential_match(stripped, source_lang, preferential_dict):
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
                    if stripped[0].isupper() and match_translation[0].islower():
                        match_translation = match_translation[0].upper() + match_translation[1:]
                    return match_translation
    return None


def _apply_preferential_replacement(cell, match_translation):
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            if run.text.strip():
                run.text = match_translation
                match_translation = ""


def _apply_ai_translation(cell, translation_manager, source_lang, target_lang,
                          use_find_replace, idx, use_cache, formatting_records,
                          preferential_dict, chunk_by):
    for paragraph in cell.paragraphs:
        idx = _translate_paragraph(
            paragraph,
            translation_manager,
            source_lang,
            target_lang,
            use_find_replace,
            idx,
            use_cache=use_cache,
            formatting_records=formatting_records,
            preferential_dict=preferential_dict,
            chunk_by=chunk_by
        )
    return idx


def _translate_table_cell(
        cell,
        translation_manager,
        source_lang,
        target_lang,
        use_find_replace,
        idx,
        use_cache=True,
        formatting_records=None,
        preferential_dict=None,
        table_translations_dict=None,
        chunk_by="sentences"
):
    to_fr = target_lang == "fr"
    cell_text = cell.text
    
    if not cell_text or not cell_text.strip():
        return idx
    
    stripped = cell_text.strip()
    
    if config.NUMERIC_CONVERSION_CONFIG.get("enabled") and is_numeric(stripped):
        _apply_numeric_conversion(cell, stripped, to_fr)
    elif table_translations_dict and stripped in table_translations_dict:
        _apply_table_dict_replacement(cell, stripped, table_translations_dict)
    elif preferential_dict and _find_preferential_match(stripped, source_lang, preferential_dict):
        match_translation = _find_preferential_match(stripped, source_lang, preferential_dict)
        _apply_preferential_replacement(cell, match_translation)
    elif len(stripped) >= config.TABLE_TRANSLATION_CONFIG.get("min_cell_length_for_ai", 20):
        return _apply_ai_translation(
            cell, translation_manager, source_lang, target_lang,
            use_find_replace, idx, use_cache, formatting_records,
            preferential_dict, chunk_by
        )
    
    return idx


def _set_proofing_language(document, target_lang):
    locale_map = {'fr': 'fr-CA', 'en': 'en-CA'}
    locale_code = locale_map[target_lang]

    elements = [document.element]

    header_footer_attrs = [
        'header', 'footer',
        'first_page_header', 'first_page_footer',
        'even_page_header', 'even_page_footer',
    ]
    seen_ids = set()
    for section in document.sections:
        for attr in header_footer_attrs:
            hf = getattr(section, attr)
            if id(hf._element) in seen_ids:
                continue
            if hf.is_linked_to_previous:
                continue
            seen_ids.add(id(hf._element))
            elements.append(hf._element)

    for root_elem in elements:
        for r_elem in root_elem.iter(qn('w:r')):
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
    formatting_records = []
    
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
            formatting_records=formatting_records,
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
                    formatting_records=formatting_records,
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
                    formatting_records=formatting_records,
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
                            formatting_records=formatting_records,
                            preferential_dict=preferential_dict,
                            table_translations_dict=table_translations_dict,
                            chunk_by=chunk_by
                        )
    
    _set_proofing_language(document, target_lang)
    document.save(output_docx_file)
    
    if formatting_records:
        notes_path = os.path.splitext(output_docx_file)[0] + '_translation_notes.docx'
        write_translations_notes(formatting_records, notes_path)
    
    return output_docx_file

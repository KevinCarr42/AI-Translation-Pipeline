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
from scitrans.translate.word_formatting import apply_formatting_rules, is_numeric, convert_numeric, parse_formatted_string
from scitrans.translate.word_notes import add_translations_notes, write_translations_notes


def _join_run_texts(all_runs):
    return ''.join(run.text or '' for run in all_runs)


def _get_run_format_key(run):
    return (
        run.bold,
        run.italic,
        run.underline,
        run.font.name,
        run.font.size,
        str(run.font.color)
    )


def _has_formatting_differences(paragraph):
    format_keys = set()
    for run in list(paragraph.runs):
        if run.text and run.text.strip():
            format_keys.add(_get_run_format_key(run))
            if len(format_keys) > 1:
                return True
    return False


def _merge_runs(paragraph):
    if _has_formatting_differences(paragraph):
        add_translations_notes(paragraph, 'inconsistent formatting')
    
    paragraph.text = paragraph.text


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
    p_elem = paragraph._element  # FIXME: is this the best way?
    hyperlink_elems = p_elem.findall(qn('w:hyperlink'))
    has_hyperlinks = len(hyperlink_elems) > 0
    
    # FIXME: clean this block up and refactor
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
                    'notes': url,
                })
        
        # Strip hyperlink XML wrappers — move w:r elements up into w:p
        for hl_elem in list(p_elem.findall(qn('w:hyperlink'))):
            for r_elem in list(hl_elem.findall(qn('w:r'))):
                p_elem.insert(list(p_elem).index(hl_elem), r_elem)
            p_elem.remove(hl_elem)
        
        _apply_cyan = True
    
    all_runs = list(paragraph.runs)
    if not all_runs:
        return idx
    
    # FIXME merge and join should be fixed and combined
    full_text = _join_run_texts(all_runs)
    
    if not full_text.strip():
        return idx
    
    # Clean up invisible run boundaries, and note formatting changes
    _merge_runs(paragraph)
    
    # Re-fetch after merge since runs may have changed
    all_runs = list(paragraph.runs)
    
    content_runs = [run for run in all_runs if run.text and run.text.strip()]
    full_text = _join_run_texts(all_runs)
    
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
    
    if _apply_cyan:
        for run in list(paragraph.runs):
            if hasattr(run, 'font') and hasattr(run.font, 'highlight_color'):
                run.font.highlight_color = WD_COLOR_INDEX.TURQUOISE
    
    return idx + 1


# FIXME: refactor into smaller helper functions for each option
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
        write_translations_notes(hyperlink_records, notes_path)  # FIXME: incl formatting notes
    
    return output_docx_file

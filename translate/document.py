import re
from translate.models import create_translator


def split_by_sentences(text):
    lines = text.split('\n')
    chunks = []
    chunk_metadata = []
    
    for line_idx, line in enumerate(lines):
        if not line.strip():
            chunks.append('')
            chunk_metadata.append({
                'line_idx': line_idx,
                'sent_idx': 0,
                'is_last_in_line': True,
                'is_empty': True
            })
            continue
        
        sentences = re.split(r'(?<=[.!?])\s+', line)
        for sent_idx, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if sentence:
                chunks.append(sentence)
                chunk_metadata.append({
                    'line_idx': line_idx,
                    'sent_idx': sent_idx,
                    'is_last_in_line': sent_idx == len(sentences) - 1,
                    'is_empty': False
                })
    
    return chunks, chunk_metadata


def reassemble_sentences(translated_chunks, chunk_metadata):
    lines_dict = {}
    for i, (translated_chunk, metadata) in enumerate(zip(translated_chunks, chunk_metadata)):
        line_idx = metadata['line_idx']
        if line_idx not in lines_dict:
            lines_dict[line_idx] = []
        
        lines_dict[line_idx].append(translated_chunk)
    
    for line_idx in lines_dict:
        if isinstance(lines_dict[line_idx], list):
            lines_dict[line_idx] = ' '.join(lines_dict[line_idx])
    
    return '\n'.join(lines_dict[i] for i in sorted(lines_dict.keys()))


def split_by_paragraphs(text):
    # Notes:
    #  still get >512 token issues with 1000 characters, use 600 to be conservative
    MAX_CHAR = 600
    
    lines = text.split('\n')
    chunks = []
    chunk_metadata = []
    
    para_idx = 0
    for line_idx, line in enumerate(lines):
        if not line.strip():
            chunks.append('')
            chunk_metadata.append({
                'line_idx': line_idx,
                'para_idx': para_idx,
                'is_empty': True
            })
            para_idx += 1
            continue
        
        if len(line) <= MAX_CHAR:
            chunks.append(line)
            chunk_metadata.append({
                'line_idx': line_idx,
                'para_idx': para_idx,
                'is_last_in_line': True,
                'is_empty': False
            })
        else:
            sentences = re.split(r'(?<=[.!?])\s+', line)
            line_chunks = []
            current_chunk = ''
            
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 1 <= MAX_CHAR:
                    current_chunk += (' ' if current_chunk else '') + sentence
                else:
                    if current_chunk:
                        line_chunks.append(current_chunk)
                    current_chunk = sentence
            
            if current_chunk:
                line_chunks.append(current_chunk)
            
            for chunk_idx, chunk in enumerate(line_chunks):
                chunks.append(chunk)
                chunk_metadata.append({
                    'line_idx': line_idx,
                    'para_idx': para_idx,
                    'is_last_in_line': chunk_idx == len(line_chunks) - 1,
                    'is_empty': False
                })
    
    return chunks, chunk_metadata


def reassemble_paragraphs(translated_chunks, chunk_metadata):
    lines_dict = {}
    for translated_chunk, metadata in zip(translated_chunks, chunk_metadata):
        line_idx = metadata['line_idx']
        if line_idx not in lines_dict:
            lines_dict[line_idx] = []
        
        lines_dict[line_idx].append(translated_chunk)
    
    for line_idx in lines_dict:
        if isinstance(lines_dict[line_idx], list):
            lines_dict[line_idx] = ' '.join(lines_dict[line_idx])
    
    return '\n'.join(lines_dict[i] for i in sorted(lines_dict.keys()))


def normalize_apostrophes(text):
    return text.replace("’", "'").replace("‘", "'")


def translate_txt_document(
        input_text_file,
        output_text_file=None,
        source_lang="en",
        chunk_by="sentences",
        models_to_use=None,
        use_find_replace=True,
        use_finetuned=True,
        translation_manager=None,
        start_idx=0,
        single_attempt=False,
        use_cache=True
):
    if not output_text_file:
        import os
        base, ext = os.path.splitext(input_text_file)
        output_text_file = f"{base}_translated{ext}"
    
    if source_lang not in ["en", "fr"]:
        raise ValueError('source_lang must be either "fr" or "en"')
    
    target_lang = "fr" if source_lang == "en" else "en"
    
    with open(input_text_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    if chunk_by == "sentences":
        chunks, chunk_metadata = split_by_sentences(text)
    else:
        chunks, chunk_metadata = split_by_paragraphs(text)
    
    if not translation_manager:
        translation_manager = create_translator(
            use_finetuned=use_finetuned,
            models_to_use=models_to_use,
            use_embedder=True,
            load_models=True
        )
    
    translated_chunks = []
    for i, (chunk, metadata) in enumerate(zip(chunks, chunk_metadata), start_idx + 1):
        if metadata.get('is_empty', False):
            translated_chunks.append('')
            continue
        
        result = translation_manager.translate_with_best_model(
            text=chunk,
            source_lang=source_lang,
            target_lang=target_lang,
            use_find_replace=use_find_replace,
            idx=i,
            single_attempt=single_attempt,
            use_cache=use_cache
        )
        
        translated_text = result.get("translated_text", "[TRANSLATION FAILED]")
        translated_text = normalize_apostrophes(translated_text)
        translated_chunks.append(translated_text)
        next_idx = i
    
    if chunk_by == "sentences":
        translated_document = reassemble_sentences(translated_chunks, chunk_metadata)
    else:
        translated_document = reassemble_paragraphs(translated_chunks, chunk_metadata)
    
    with open(output_text_file, 'w', encoding='utf-8') as f:
        f.write(translated_document)
    
    return next_idx if translated_chunks else start_idx


def _get_run_format_key(run):
    font_color = None
    if run.font.color and run.font.color.rgb:
        font_color = str(run.font.color.rgb)
    
    return (
        run.bold,
        run.italic,
        run.underline,
        run.font.name,
        run.font.size,
        font_color
    )


def _merge_identical_runs(paragraph):
    if len(paragraph.runs) <= 1:
        return
    
    # Build list of (run, format_key) pairs for runs with content
    run_info = []
    for run in paragraph.runs:
        if run.text:
            run_info.append((run, _get_run_format_key(run)))
    
    if len(run_info) <= 1:
        return
    
    # Merge adjacent runs with identical formatting
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
    
    for run in paragraph.runs:
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
    for run in paragraph.runs:
        if run.text.strip():
            format_keys.add(_get_run_format_key(run))
            if len(format_keys) > 1:
                return True
    return False


def _translate_paragraph(paragraph, translation_manager, source_lang, target_lang, use_find_replace, idx, use_cache=True):
    if not paragraph.runs:
        return idx
    
    run_texts = [run.text for run in paragraph.runs]
    full_text = ''.join(run_texts)
    
    if not full_text.strip():
        return idx
    
    # Clean up invisible run boundaries by merging identical adjacent runs
    _merge_identical_runs(paragraph)
    
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
        
        result = translation_manager.translate_with_best_model(
            text=text_to_translate,
            source_lang=source_lang,
            target_lang=target_lang,
            use_find_replace=use_find_replace,
            idx=idx,
            use_cache=use_cache
        )
        
        translated_text = result.get("translated_text", "[TRANSLATION FAILED]")
        translated_text = normalize_apostrophes(translated_text)
        
        first_content_run = None
        for run in paragraph.runs:
            if run.text.strip():
                first_content_run = run
                break
        
        if first_content_run:
            first_content_run.text = leading_ws + translated_text + trailing_ws
            found_first = False
            for run in paragraph.runs:
                if run.text.strip():
                    if found_first:
                        run.text = ''
                    else:
                        found_first = True
        
        return idx + 1
    
    # Has formatting differences - use segment-based translation
    segments = _build_format_segments(paragraph)
    
    if not segments:
        return idx
    
    for segment_idx, segment_runs in enumerate(segments):
        segment_text = ''.join(run.text for run in segment_runs)
        
        if not segment_text.strip():
            continue
        
        # Handle leading/trailing whitespace for segment
        leading_ws = ''
        trailing_ws = ''
        text_to_translate = segment_text
        
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
            continue
        
        result = translation_manager.translate_with_best_model(
            text=text_to_translate,
            source_lang=source_lang,
            target_lang=target_lang,
            use_find_replace=use_find_replace,
            idx=idx,
            use_cache=use_cache
        )
        
        translated_text = result.get("translated_text", "[TRANSLATION FAILED]")
        translated_text = normalize_apostrophes(translated_text)
        
        # Put translated text in first run of segment, clear others
        segment_runs[0].text = leading_ws + translated_text + trailing_ws
        for run in segment_runs[1:]:
            run.text = ''
        
        idx += 1
    
    return idx


def translate_word_document(
        input_docx_file,
        output_docx_file=None,
        source_lang="en",
        models_to_use=None,
        use_find_replace=True,
        use_finetuned=True,
        translation_manager=None,
        include_timestamp=True,
        use_cache=True
):
    import os
    from datetime import datetime
    from docx import Document
    
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
    
    for paragraph in document.paragraphs:
        idx = _translate_paragraph(paragraph, translation_manager, source_lang, target_lang, use_find_replace, idx, use_cache=use_cache)
    
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    idx = _translate_paragraph(paragraph, translation_manager, source_lang, target_lang, use_find_replace, idx, use_cache=use_cache)
    
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
                idx = _translate_paragraph(paragraph, translation_manager, source_lang, target_lang, use_find_replace, idx, use_cache=use_cache)
            for table in hf.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            idx = _translate_paragraph(paragraph, translation_manager, source_lang, target_lang, use_find_replace, idx, use_cache=use_cache)
    
    document.save(output_docx_file)
    return output_docx_file

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
    #  at 2000 char, we get significant preferential translation errors
    #  at 1000 char, we get the same errors
    MAX_CHAR = 1000
    
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks = []
    chunk_metadata = []
    
    for para_idx, para in enumerate(paragraphs):
        if len(para) <= MAX_CHAR:
            chunks.append(para)
            chunk_metadata.append({'para_idx': para_idx, 'is_last_in_para': True})
        else:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            current_chunk = ''
            para_chunks = []
            
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 1 <= MAX_CHAR:
                    current_chunk += (' ' if current_chunk else '') + sentence
                else:
                    if current_chunk:
                        para_chunks.append(current_chunk)
                    current_chunk = sentence
            
            if current_chunk:
                para_chunks.append(current_chunk)
            
            for chunk_idx, chunk in enumerate(para_chunks):
                chunks.append(chunk)
                chunk_metadata.append({
                    'para_idx': para_idx,
                    'is_last_in_para': chunk_idx == len(para_chunks) - 1
                })
    
    return chunks, chunk_metadata


def reassemble_paragraphs(translated_chunks, chunk_metadata):
    paras_dict = {}
    for translated_chunk, metadata in zip(translated_chunks, chunk_metadata):
        para_idx = metadata['para_idx']
        if para_idx not in paras_dict:
            paras_dict[para_idx] = []
        
        paras_dict[para_idx].append(translated_chunk)
    
    paragraphs = []
    for para_idx in sorted(paras_dict.keys()):
        paragraphs.append(' '.join(paras_dict[para_idx]))
    
    return '\n\n'.join(paragraphs)


def normalize_apostrophes(text):
    return text.replace("’", "'").replace("‘", "'")


def translate_document(
        input_text_file,
        output_text_file=None,
        source_lang="en",
        chunk_by="sentences",
        models_to_use=None,
        use_find_replace=True,
        use_finetuned=True,
        translation_manager=None
):
    if not output_text_file:
        output_text_file = input_text_file.replace(input_text_file[-4], "_translated" + input_text_file[-4])
    
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
    for i, (chunk, metadata) in enumerate(zip(chunks, chunk_metadata), 1):
        if chunk_by == "sentences" and metadata.get('is_empty', False):
            translated_chunks.append('')
            continue
        
        result = translation_manager.translate_with_best_model(
            text=chunk,
            source_lang=source_lang,
            target_lang=target_lang,
            use_find_replace=use_find_replace,
            idx=i
        )
        
        translated_text = result.get("translated_text", "[TRANSLATION FAILED]")
        translated_text = normalize_apostrophes(translated_text)
        translated_chunks.append(translated_text)
    
    if chunk_by == "sentences":
        translated_document = reassemble_sentences(translated_chunks, chunk_metadata)
    else:
        translated_document = reassemble_paragraphs(translated_chunks, chunk_metadata)
    
    with open(output_text_file, 'w', encoding='utf-8') as f:
        f.write(translated_document)

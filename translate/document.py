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


def split_by_paragraphs(text):
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    return paragraphs, None


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
        lines_dict = {}
        for i, (translated_chunk, metadata) in enumerate(zip(translated_chunks, chunk_metadata)):
            line_idx = metadata['line_idx']
            if line_idx not in lines_dict:
                lines_dict[line_idx] = []
            
            lines_dict[line_idx].append(translated_chunk)
        
        for line_idx in lines_dict:
            if isinstance(lines_dict[line_idx], list):
                lines_dict[line_idx] = ' '.join(lines_dict[line_idx])
        
        translated_document = '\n'.join(lines_dict[i] for i in sorted(lines_dict.keys()))
    else:
        translated_document = '\n\n'.join(translated_chunks)
    
    with open(output_text_file, 'w', encoding='utf-8') as f:
        f.write(translated_document)

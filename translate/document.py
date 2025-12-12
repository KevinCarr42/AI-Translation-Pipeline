import re
from translate.models import create_translator


def split_by_sentences(text):
    paragraphs = text.split('\n\n')
    chunks = []
    chunk_metadata = []
    
    for para_idx, paragraph in enumerate(paragraphs):
        if not paragraph.strip():
            continue
        
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        for sent_idx, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if sentence:
                chunks.append(sentence)
                chunk_metadata.append({
                    'para_idx': para_idx,
                    'sent_idx': sent_idx,
                    'is_last_in_para': sent_idx == len(sentences) - 1
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
    for i, chunk in enumerate(chunks, 1):
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
        paragraphs_dict = {}
        for i, (translated_chunk, metadata) in enumerate(zip(translated_chunks, chunk_metadata)):
            para_idx = metadata['para_idx']
            if para_idx not in paragraphs_dict:
                paragraphs_dict[para_idx] = []
            
            paragraphs_dict[para_idx].append(translated_chunk)
        
        for para_idx in paragraphs_dict:
            if isinstance(paragraphs_dict[para_idx], list):
                paragraphs_dict[para_idx] = ' '.join(paragraphs_dict[para_idx])
        
        translated_document = '\n\n'.join(paragraphs_dict[i] for i in sorted(paragraphs_dict.keys()))
    else:
        translated_document = '\n\n'.join(translated_chunks)
    
    with open(output_text_file, 'w', encoding='utf-8') as f:
        f.write(translated_document)

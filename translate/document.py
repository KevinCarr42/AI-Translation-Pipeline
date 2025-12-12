import config
import os
import re
from translate.models import OpusTranslationModel, M2M100TranslationModel, MBART50TranslationModel, create_translator


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


def _get_model_config(use_finetuned=True):
    model_class_map = {
        "OpusTranslationModel": OpusTranslationModel,
        "M2M100TranslationModel": M2M100TranslationModel,
        "MBART50TranslationModel": MBART50TranslationModel,
    }
    
    all_models = {}
    for variant_name, variant_config in config.TRANSLATION_MODEL_VARIANTS.items():
        if not use_finetuned and variant_config["use_finetuned"]:
            continue
        
        base_model_key = variant_config["base_model_key"]
        base_model = config.MODELS[base_model_key]
        
        params = {
            "base_model_id": base_model["model_id"],
            "model_type": base_model["type"],
        }
        
        if "merged_model_names" in variant_config:
            for path_key, model_name in variant_config["merged_model_names"].items():
                params[path_key] = os.path.join(config.MERGED_MODEL_DIR, model_name)
        
        all_models[variant_name] = {
            "cls": model_class_map[variant_config["model_class"]],
            "params": params
        }
    
    return all_models


def translate_document(
        input_text_file,
        output_text_file=None,
        source_lang="en",
        chunk_by="sentences",
        models_to_use=None,
        use_find_replace=True,
        use_finetuned=True,
        debug=False
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
    
    all_models = _get_model_config(use_finetuned)
    
    if models_to_use:
        all_models = {k: v for k, v in all_models.items() if k in models_to_use}
    
    if debug:
        print(f"Loading embedder...")
    
    translation_manager = create_translator(all_models, use_embedder=True)
    if debug:
        print(f"Loading models...")
    translation_manager.load_models()
    
    translated_chunks = []
    total = len(chunks)
    
    if debug:
        print(f"Translating {total} chunks from {source_lang} to {target_lang}...")
    
    for i, chunk in enumerate(chunks, 1):
        result = translation_manager.translate_with_best_model(
            text=chunk,
            source_lang=source_lang,
            target_lang=target_lang,
            use_find_replace=use_find_replace,
            idx=i
        )
        
        translated_text = result.get("translated_text", "[TRANSLATION FAILED]")
        translated_chunks.append(translated_text)
    
    if chunk_by == "sentences":
        paragraphs_dict = {}
        for i, (translated_chunk, metadata) in enumerate(zip(translated_chunks, chunk_metadata)):
            para_idx = metadata['para_idx']
            if para_idx not in paragraphs_dict:
                paragraphs_dict[para_idx] = []
            
            paragraphs_dict[para_idx].append(translated_chunk)
            
            if metadata['is_last_in_para']:
                paragraphs_dict[para_idx] = ' '.join(paragraphs_dict[para_idx])
        
        translated_document = '\n\n'.join(paragraphs_dict[i] for i in sorted(paragraphs_dict.keys()))
    else:
        translated_document = '\n\n'.join(translated_chunks)
    
    with open(output_text_file, 'w', encoding='utf-8') as f:
        f.write(translated_document)
    
    if debug:
        print(f"Translation complete! Output saved to: {output_text_file}")

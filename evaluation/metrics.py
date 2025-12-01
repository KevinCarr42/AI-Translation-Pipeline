import torch
from sentence_transformers.util import pytorch_cos_sim


def calculate_cosine_similarity(embedder, text1, text2):
    embedding1 = embedder.encode(text1, convert_to_tensor=True)
    embedding2 = embedder.encode(text2, convert_to_tensor=True)
    similarity = pytorch_cos_sim(embedding1, embedding2).item()
    return similarity


def check_token_prefix_error(translated_text, original_text, token_prefixes=None):
    if token_prefixes is None:
        token_prefixes = ['NOMENCLATURE', 'TAXON', 'ACRONYM', 'SITE']

    for token_prefix in token_prefixes:
        if token_prefix in translated_text:
            if not original_text or token_prefix not in original_text:
                return True
    return False


def is_valid_translation(translated_text, original_text, token_mapping=None, token_prefixes=None):
    if check_token_prefix_error(translated_text, original_text, token_prefixes):
        return False

    if token_mapping:
        for key in token_mapping.keys():
            if key not in translated_text:
                return False

    return True


def calculate_similarity_scores(embedder, source_text, translated_text, target_text=None):
    source_embedding = embedder.encode(source_text, convert_to_tensor=True)
    translated_embedding = embedder.encode(translated_text, convert_to_tensor=True)
    similarity_vs_source = pytorch_cos_sim(source_embedding, translated_embedding).item()

    similarity_vs_target = None
    similarity_of_original_translation = None

    if target_text:
        target_embedding = embedder.encode(target_text, convert_to_tensor=True)
        similarity_vs_target = pytorch_cos_sim(target_embedding, translated_embedding).item()
        similarity_of_original_translation = pytorch_cos_sim(source_embedding, target_embedding).item()

    return {
        'similarity_vs_source': similarity_vs_source,
        'similarity_vs_target': similarity_vs_target,
        'similarity_of_original_translation': similarity_of_original_translation,
    }

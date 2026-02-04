import json
import os
import random
import pandas as pd
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import pytorch_cos_sim

from translate.models import create_translator
from translate.document import translate_document

TEMP_DIR = os.path.join(os.path.dirname(__file__), "eval_results", "quality")
DEFAULT_OUTPUT_PICKLE = os.path.join(os.path.dirname(__file__), "eval_results", "quality_test_results.pickle")


def load_testing_data(jsonl_path):
    data = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def sample_testing_data(data, n=None, seed=None):
    if n is None or n >= len(data):
        return data
    if seed is not None:
        random.seed(seed)
    return random.sample(data, n)


def run_quality_evaluation(
        models_to_use,
        jsonl_path,
        n_samples=None,
        seed=None,
        use_find_replace=True,
        compare_find_replace=True,
        output_pickle=None
):
    if output_pickle is None:
        output_pickle = DEFAULT_OUTPUT_PICKLE
    
    data = load_testing_data(jsonl_path)
    if n_samples:
        data = sample_testing_data(data, n_samples, seed)
    
    embedder = SentenceTransformer('sentence-transformers/LaBSE')
    
    translation_managers = {}
    for model_name in models_to_use:
        print(f"Loading model: {model_name}")
        translation_managers[model_name] = create_translator(
            models_to_use=[model_name],
            use_embedder=False,
            load_models=True
        )
    
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    results = []
    
    for idx, row in enumerate(data):
        source_text = row["source"]
        source_lang = row["source_lang"]
        target_text = row["target"]
        
        print(f"Processing sample {idx + 1}/{len(data)}")
        
        source_embedding = embedder.encode(source_text, convert_to_tensor=True)
        
        target_embedding = embedder.encode(target_text, convert_to_tensor=True)
        target_similarity = pytorch_cos_sim(source_embedding, target_embedding).item()
        
        results.append({
            "sample_idx": idx,
            "source_text": source_text,
            "source_lang": source_lang,
            "translator": "human_target",
            "use_find_replace": None,
            "translated_text": target_text,
            "similarity_vs_source": target_similarity
        })
        
        input_file = os.path.join(TEMP_DIR, f"source_{idx}.txt")
        with open(input_file, 'w', encoding='utf-8') as f:
            f.write(source_text)
        
        for model_name, manager in translation_managers.items():
            find_replace_options = [True, False] if compare_find_replace else [use_find_replace]
            for fr_option in find_replace_options:
                suffix = "fr" if fr_option else "nofr"
                output_file = os.path.join(TEMP_DIR, f"output_{model_name}_{suffix}_{idx}.txt")
                
                translate_document(
                    input_text_file=input_file,
                    output_text_file=output_file,
                    source_lang=source_lang,
                    chunk_by="sentences",
                    use_find_replace=fr_option,
                    translation_manager=manager,
                    single_attempt=True
                )
                
                with open(output_file, 'r', encoding='utf-8') as f:
                    translated_text = f.read()
                
                translated_embedding = embedder.encode(translated_text, convert_to_tensor=True)
                similarity = pytorch_cos_sim(source_embedding, translated_embedding).item()
                
                results.append({
                    "sample_idx": idx,
                    "source_text": source_text,
                    "source_lang": source_lang,
                    "translator": model_name,
                    "use_find_replace": fr_option,
                    "translated_text": translated_text,
                    "similarity_vs_source": similarity
                })
                
                if os.path.exists(output_file):
                    os.remove(output_file)
        
        if os.path.exists(input_file):
            os.remove(input_file)
    
    df = pd.DataFrame(results)
    
    os.makedirs(os.path.dirname(output_pickle), exist_ok=True)
    df.to_pickle(output_pickle)
    
    print(f"Results saved to {output_pickle}")

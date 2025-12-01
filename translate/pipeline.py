from sentence_transformers import SentenceTransformer
from .models import TranslationManager
from .document import translate_document


def translation_pipeline(input_text_file, output_text_file, with_preferential_translation=True,
                         source_lang="en", chunk_by="sentences", models_to_use=None, use_finetuned=True, debug=False):
    print("\n" + "=" * 60)
    print("Translation Pipeline")
    print("=" * 60)
    print(f"Using preferential translation: {with_preferential_translation}\n")
    
    if with_preferential_translation:
        print("Preferential translation is enabled")
        print("Terminology will be preserved using token replacement\n")
    else:
        print("Preferential translation is disabled")
        print("Using raw model output\n")
    
    print(f"Translating document: {input_text_file}")
    print(f"Source language: {source_lang}")
    print(f"Chunk strategy: {chunk_by}")
    print(f"Using fine-tuned models: {use_finetuned}\n")
    
    translate_document(
        input_text_file=input_text_file,
        output_text_file=output_text_file,
        source_lang=source_lang,
        chunk_by=chunk_by,
        models_to_use=models_to_use,
        use_find_replace=with_preferential_translation,
        use_finetuned=use_finetuned,
        debug=debug
    )
    
    return {"status": "complete", "output_file": output_text_file}


def create_translator(all_models, use_embedder=True):
    embedder = None
    if use_embedder:
        embedder = SentenceTransformer('sentence-transformers/LaBSE')
    
    return TranslationManager(all_models, embedder)

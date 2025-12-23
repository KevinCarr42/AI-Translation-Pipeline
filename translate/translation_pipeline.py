from translate.document import translate_document


def translation_pipeline(input_text_file, output_text_file, with_terminology=True,
                         source_lang="en", chunk_by="sentences", models_to_use=None, use_finetuned=True):
    print("\n" + "=" * 60)
    print("Translation Pipeline")
    print("=" * 60)
    print(f"Using terminology constraints: {with_terminology}\n")

    if with_terminology:
        print("Terminology constraints are enabled")
        print("Lexically constrained decoding will enforce terminology\n")
    else:
        print("Terminology constraints are disabled")
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
        use_terminology=with_terminology,
        use_finetuned=use_finetuned
    )

    return {"status": "complete", "output_file": output_text_file}

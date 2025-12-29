import config
import os
from translate.document import translate_document
from translate.models import create_translator

if __name__ == '__main__':
    use_finetuned = True
    
    file_list = (
        ("example0.txt", "en"), ("example0_translated.txt", "fr"),
        # ("example1.txt", "en"), ("example1_translated.txt", "fr"),
        # ("example2.txt", "en"), ("example2_translated.txt", "fr"),
        # ("example3.txt", "en"), ("example3_translated.txt", "fr"),
        # ("example4.txt", "en"), ("example4_translated.txt", "fr"),
    )
    
    translation_manager = create_translator(
        use_finetuned=use_finetuned,
        # models_to_use=['opus_mt_finetuned']
    )
    for filename, source_lang in file_list:
        translate_document(
            input_text_file=os.path.join(config.TRANSLATED_TEXT_DIR, filename),
            output_text_file=None,
            source_lang=source_lang,
            chunk_by="paragraph",
            models_to_use=None,
            use_find_replace=True,
            use_finetuned=None,
            translation_manager=translation_manager
        )

import config
import os
from translate.document import translate_document
from translate.models import create_translator


if __name__ == '__main__':
    file_list = (("example.txt", "en"), ("example2.txt", "en"))
    
    translation_manager = create_translator()
    for filename, source_lang in file_list:
        translate_document(
            input_text_file=os.path.join(config.TRANSLATED_TEXT_DIR, filename),
            output_text_file=None,
            source_lang=source_lang,
            chunk_by="sentences",
            models_to_use=None,
            use_find_replace=True,
            use_finetuned=True,
            translation_manager=translation_manager
        )

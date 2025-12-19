import config
import os
from translate.document import translate_document
from translate.models import create_translator


if __name__ == '__main__':
    file_list = (
        ("example1.txt", "en"), ("example1_translated.txt", "fr"),
        ("example2.txt", "en"), ("example2_translated.txt", "fr"),
        ("example3.txt", "en"), ("example3_translated.txt", "fr"),
        ("example4.txt", "en"), ("example4_translated.txt", "fr"),
    )
    
    translation_manager = create_translator()
    for filename, source_lang in file_list:
        translate_document(
            input_text_file=os.path.join(config.TRANSLATED_TEXT_DIR, filename),
            output_text_file=None,
            source_lang=source_lang,
            chunk_by="paragraph",
            models_to_use=None,
            use_find_replace=True,
            use_finetuned=True,
            translation_manager=translation_manager
        )

# FIXME (paragraphs)
#  C:\Users\CARRK\Documents\Repositories\AI\Pipeline\.venv\Scripts\python.exe C:\Users\CARRK\Documents\Repositories\AI\Pipeline\translate_documents.py
#    `torch_dtype` is deprecated! Use `dtype` instead!
#    	No valid translations found following 8 attempted configs.
#    	No valid translations found following 8 attempted configs.
#    	No valid translations found following 8 attempted configs.
#    	No valid translations found following 8 attempted configs.
#    	No valid translations found following 8 attempted configs.
#    	No valid translations found following 8 attempted configs.
#    	Valid translation following 7 retries.
#    	No valid translations found following 8 attempted configs.

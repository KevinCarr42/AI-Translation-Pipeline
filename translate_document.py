import config
import os
from translate.document import translate_document

if __name__ == '__main__':
    filename = "example.txt"
    source_lang = "en"
    
    translate_document(
        input_text_file=os.path.join(config.TRANSLATED_TEXT_DIR, filename),
        output_text_file=None,
        source_lang=source_lang,
        chunk_by="sentences",
        models_to_use=None,
        use_find_replace=True,
        use_finetuned=True,
        debug=False
    )

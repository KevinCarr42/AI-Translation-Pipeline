import config
import os
import time
from translate.document import translate_document
from translate.models import create_translator

if __name__ == '__main__':
    print_timing = True
    if print_timing:
        start_time = time.time()
        print(f"Start time: {time.ctime(start_time)}")
    
    use_finetuned = True
    
    file_list = (
        ("example0.txt", "en"), ("example0_translated.txt", "fr"),
        ("example1.txt", "en"), ("example1_translated.txt", "fr"),
        ("example2.txt", "en"), ("example2_translated.txt", "fr"),
        ("example3.txt", "en"), ("example3_translated.txt", "fr"),
    )
    
    translation_manager = create_translator(
        use_finetuned=use_finetuned,
        # models_to_use=['opus_mt_finetuned']
    )
    
    if print_timing:
        init_done_time = time.time()
        print(f"Manager initialized: {init_done_time - start_time:.2f}s")
        loop_prev_time = init_done_time
    
    for filename, source_lang in file_list:
        translate_document(
            input_text_file=os.path.join(config.TRANSLATED_TEXT_DIR, filename),
            output_text_file=None,
            source_lang=source_lang,
            chunk_by="sentence",
            models_to_use=None,
            use_find_replace=True,
            use_finetuned=None,
            translation_manager=translation_manager,
            single_attempt=False
        )
        
        if print_timing:
            loop_end_time = time.time()
            print(f"Finished {filename}: {loop_end_time - loop_prev_time:.2f}s")
            loop_prev_time = loop_end_time
    
    if print_timing:
        end_time = time.time()
        print(f"Total execution time: {end_time - start_time:.2f}s")

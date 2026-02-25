import config
import time
from pathlib import Path
from translate.document import translate_txt_document, translate_word_document
from translate.models import create_translator

if __name__ == '__main__':
    print_timing = True
    clear_cache_between_docs = True
    
    if print_timing:
        start_time = time.time()
        print(f"Start time: {time.ctime(start_time)}")
    
    use_finetuned = True
    
    file_list = (
        # ("1432_en.docx", "en"),
        # ("1466_fr.docx", "fr"),
        # ("EXAMPLE_PROBLEM.docx", "en"),
        ("EXAMPLE_PROBLEM_all_black.docx", "en"),
    )
    
    translation_manager = create_translator(
        use_finetuned=use_finetuned,
        debug = True
    )
    
    if print_timing:
        init_done_time = time.time()
        print(f"Manager initialized: {init_done_time - start_time:.2f}s")
        loop_prev_time = init_done_time
    
    for filename, source_lang in file_list:
        if clear_cache_between_docs:
            translation_manager.clear_errors()
        file_path = Path(config.TRANSLATED_TEXT_DIR) / filename
        
        if not file_path.exists():
            print(f"Skipping {filename}: file not found")
            continue
        
        extension = file_path.suffix.lower()
        
        if 'doc' in extension:
            translate_word_document(
                input_docx_file=str(file_path),
                output_docx_file=None,
                source_lang=source_lang,
                models_to_use=None,
                use_find_replace=True,
                use_finetuned=None,
                translation_manager=translation_manager,
                include_timestamp=False,
                use_cache=True
            )
        else:
            translate_txt_document(
                input_text_file=str(file_path),
                output_text_file=None,
                source_lang=source_lang,
                chunk_by="sentence",
                models_to_use=None,
                use_find_replace=True,
                use_finetuned=None,
                translation_manager=translation_manager,
                single_attempt=False,
                use_cache=True
            )
        
        if print_timing:
            loop_end_time = time.time()
            print(f"Finished {filename}: {loop_end_time - loop_prev_time:.2f}s")
            loop_prev_time = loop_end_time
    
    if print_timing:
        end_time = time.time()
        print(f"Total execution time: {end_time - start_time:.2f}s")

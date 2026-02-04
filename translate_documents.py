import config
import os
import time
from translate.document import translate_document
from translate.models import create_translator

if __name__ == '__main__':
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
        
        loop_end_time = time.time()
        print(f"Finished {filename}: {loop_end_time - loop_prev_time:.2f}s")
        loop_prev_time = loop_end_time
    
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f}s")


"""
Seems like bugfixes are neutral or good depending on the complexity
- overall look good
- docs translate the same with both methods based on spot check


==== with all models ====

======== WITH BUGFIXES ========

Start time: Wed Feb  4 10:15:50 2026
`torch_dtype` is deprecated! Use `dtype` instead!
Manager initialized: 23.90s
Finished example0.txt: 1.10s
Finished example0_translated.txt: 13.30s
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
Finished example1.txt: 20.04s
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
Finished example1_translated.txt: 14.15s
Finished example2.txt: 38.79s
Finished example2_translated.txt: 31.83s
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	Valid translation following 1 retries.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
Finished example3.txt: 97.07s
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	Valid translation following 7 retries.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	Valid translation following 7 retries.
Finished example3_translated.txt: 88.11s
Total execution time: 328.29s

======== WITHOUT BUGFIXES ========

Start time: Wed Feb  4 10:45:28 2026
`torch_dtype` is deprecated! Use `dtype` instead!
Manager initialized: 91.69s
Finished example0.txt: 6.68s
Finished example0_translated.txt: 60.94s
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
Finished example1.txt: 128.27s
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
Finished example1_translated.txt: 90.69s
Finished example2.txt: 76.68s
Finished example2_translated.txt: 33.91s
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
Finished example3.txt: 106.56s
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	Valid translation following 7 retries.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
Finished example3_translated.txt: 235.91s
Total execution time: 831.35s

==== with opus only ====

======== WITH BUGFIXES ========

Start time: Wed Feb  4 10:25:20 2026
`torch_dtype` is deprecated! Use `dtype` instead!
Manager initialized: 10.13s
Finished example0.txt: 0.23s
Finished example0_translated.txt: 2.45s
Finished example1.txt: 0.47s
Finished example1_translated.txt: 0.57s
Finished example2.txt: 4.18s
Finished example2_translated.txt: 3.39s
	No valid translations found following 8 attempted configs.
Finished example3.txt: 9.53s
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
Finished example3_translated.txt: 9.52s
Total execution time: 40.47s

Process finished with exit code 0

======== WITHOUT BUGFIXES ========

Start time: Wed Feb  4 10:44:11 2026
`torch_dtype` is deprecated! Use `dtype` instead!
Manager initialized: 6.99s
Finished example0.txt: 0.20s
Finished example0_translated.txt: 2.54s
Finished example1.txt: 0.47s
Finished example1_translated.txt: 0.45s
Finished example2.txt: 3.86s
Finished example2_translated.txt: 3.29s
	No valid translations found following 8 attempted configs.
Finished example3.txt: 9.24s
	No valid translations found following 8 attempted configs.
	No valid translations found following 8 attempted configs.
Finished example3_translated.txt: 9.18s
Total execution time: 36.20s

"""
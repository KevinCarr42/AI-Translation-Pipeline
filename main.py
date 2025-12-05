import os
import config

from create_training_data.pipeline import create_training_data_pipeline
from model_finetuning.pipeline import finetuning_pipeline
from translate import translation_pipeline


def translate_text(
        input_text_filename,
        with_preferential_translation=True,
        source_lang="en"
):
    target_lang = "fr" if source_lang == "en" else "en"
    output_text_filename = input_text_filename.replace(".txt", f"_{target_lang}.txt")
    input_text_file = os.path.join(config.TRANSLATED_TEXT_DIR, input_text_filename)
    output_text_file = os.path.join(config.TRANSLATED_TEXT_DIR, output_text_filename)
    
    translation_pipeline(
        input_text_file=input_text_file,
        output_text_file=output_text_file,
        with_preferential_translation=with_preferential_translation,
        source_lang=source_lang,
    )


if __name__ == "__main__":
    create_training_data_pipeline()

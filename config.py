import os

# folders
DATA_DIR = "../Data"
MODEL_OUTPUT_DIR = "../outputs"
TRANSLATED_TEXT_DIR = "translations"

# starting data
PARSED_DOCS_DIR = os.path.join(DATA_DIR, "ParsedPublications")
CORRELATION_CSV_PATH = os.path.join(DATA_DIR, "fr_eng_correlation_data.csv")
PREFERENTIAL_JSON_PATH = os.path.join(DATA_DIR, "preferential_translations.json")

# calculated data
MATCHED_DATA = os.path.join(DATA_DIR, "pipeline_matched_data.pickle")  # tested, works
MATCHED_DATA_WITH_FEATURES = os.path.join(DATA_DIR, "pipeline_df_with_features.pickle")
MATCHED_DATA_WITH_ALL_FEATURES = os.path.join(DATA_DIR, "pipeline_df_with_more_features.pickle")

# training and testing data
TRAINING_DATA_OUTPUT = os.path.join(DATA_DIR, "pipeline_training_data.jsonl")
TESTING_DATA_OUTPUT = os.path.join(DATA_DIR, "pipeline_testing_data.jsonl")

# pretrained and finetuned folders
PRETRAINED_MODELS_FOLDER = os.path.join(DATA_DIR, "pretrained_models")
FINETUNED_MODELS_FOLDER = os.path.join(DATA_DIR, "merged")

MODELS = {
    "m2m100_418m": {
        "model_id": "facebook/m2m100_418M",
        "type": "seq2seq",
        "language_map": {"en": "en", "fr": "fr"}
    },
    "mbart50_mmt_fr": {
        "model_id": "facebook/mbart-large-50-many-to-many-mmt",
        "type": "seq2seq",
        "language_map": {"en": "en_XX", "fr": "fr_XX"},
        "restrict_source_language": "en"
    },
    "mbart50_mmt_en": {
        "model_id": "facebook/mbart-large-50-many-to-many-mmt",
        "type": "seq2seq",
        "language_map": {"en": "en_XX", "fr": "fr_XX"},
        "restrict_source_language": "fr"
    },
    "opus_mt_en_fr": {
        "model_id": "Helsinki-NLP/opus-mt-tc-big-en-fr",
        "type": "seq2seq",
        "language_map": {"en": "en", "fr": "fr"},
        "restrict_source_language": "en"
    },
    "opus_mt_fr_en": {
        "model_id": "Helsinki-NLP/opus-mt-tc-big-fr-en",
        "type": "seq2seq",
        "language_map": {"en": "en", "fr": "fr"},
        "restrict_source_language": "fr"
    },
}

TRAINING_HYPERPARAMS = {
    "learning_rate": 2e-4,
    "batch_size": 8,
    "gradient_accumulation": 2,
    "epochs": 1.0,
    "lora_r": 32,
    "lora_alpha": 64,
    "lora_dropout": 0.05,
    "max_source_length": 512,
    "max_target_length": 512,
    "validation_ratio": 0.05,
    "warmup_ratio": 0.03,
    "seed": 42,
    "weight_decay": 0.01,
    "label_smoothing": 0.1,
    "eval_steps": 1000,
    "logging_steps": 50,
    "save_steps": 1000,
}

MODEL_SPECIFIC_HYPERPARAMS = {
    "m2m100_418m": {
        "batch_size": 12,
        "learning_rate": 2e-4,
        "lora_r": 32,
        "lora_alpha": 64,
    },
    "mbart50_mmt_fr": {
        "batch_size": 8,
        "learning_rate": 1.5e-4,
        "lora_r": 32,
        "lora_alpha": 64,
    },
    "mbart50_mmt_en": {
        "batch_size": 8,
        "learning_rate": 1.5e-4,
        "lora_r": 32,
        "lora_alpha": 64,
    },
    "opus_mt_en_fr": {
        "batch_size": 16,
        "learning_rate": 3e-4,
        "lora_r": 32,
        "lora_alpha": 64,
    },
    "opus_mt_fr_en": {
        "batch_size": 16,
        "learning_rate": 3e-4,
        "lora_r": 32,
        "lora_alpha": 64,
    },
}

QUANTIZATION_CONFIG = {
    "use_quantization": False,
    "use_qlora": False,
    "use_bfloat16": True,
    "use_fp16": False,
}

DEVICE_CONFIG = {
    "device_map": "auto",
    "offload_folder": "./offload",
}

DATA_CLEANING_CONFIG = {
    "skip_cleaning": False,
    "linebreaks": True,
    "add_features": True,
    "skip_abstracts": False,
}

EVALUATION_CONFIG = {
    "use_similarity": True,
    "use_quality": True,
    "use_comparison": True,
}

PREFERENTIAL_TRANSLATION_CONFIG = {
    "use_replacements": True,
    "validate_tokens": True,
}

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODEL_OUTPUT_DIR, exist_ok=True)

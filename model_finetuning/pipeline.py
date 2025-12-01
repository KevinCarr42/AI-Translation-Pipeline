import os
import json
import logging
import math
from datasets import load_dataset

from .model_loading import load_tokenizer_and_model
from .preprocessing import Preprocessor
from .trainer import build_trainer


def setup_logging(output_directory, to_file=True):
    os.makedirs(output_directory, exist_ok=True)
    handlers = [logging.StreamHandler()]
    if to_file:
        handlers.append(logging.FileHandler(os.path.join(output_directory, "console_output.txt"), encoding="utf-8"))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", handlers=handlers)


def filter_dataset_by_model(dataset, model_config):
    if "restrict_source_language" not in model_config:
        return dataset
    allowed_lang = model_config["restrict_source_language"]
    return dataset.filter(lambda x: x["source_lang"] == allowed_lang)


def finetune_model(model_name, data_path, output_directory, learning_rate=2e-4, batch_size=8, gradient_accumulation=2, epochs=2.0, eval_steps=1000, logging_steps=50, save_steps=1000, seed=42, warmup_ratio=0.03, validation_ratio=0.05, max_source_length=512, max_target_length=512, use_bfloat16=False, use_fp16=True, use_qlora=True, device_map="auto", disable_tqdm=True, lora_r=16, lora_alpha=32, lora_dropout=0.05, max_steps=None):

    import config
    from peft import LoraConfig, get_peft_model
    import torch

    model_info = config.MODELS.get(model_name)
    if not model_info:
        raise ValueError(f"Model '{model_name}' not found in config.MODELS")

    raw_dataset = load_dataset("json", data_files=data_path, split="train")
    raw_dataset = filter_dataset_by_model(raw_dataset, model_info)

    if len(raw_dataset) == 0:
        raise ValueError(f"No data remaining after filtering for model {model_name}")

    split_dataset = raw_dataset.train_test_split(test_size=validation_ratio, seed=seed)
    train_dataset = split_dataset["train"].shuffle(seed=seed)
    eval_dataset = split_dataset["test"].shuffle(seed=seed)

    is_opus_model = "opus_mt" in model_name
    if use_qlora:
        resolved_device_map = None if is_opus_model else device_map
    else:
        resolved_device_map = None if is_opus_model else device_map

    tokenizer, _ = load_tokenizer_and_model(
        model_info["model_id"],
        use_qlora=use_qlora,
        use_bfloat16=use_bfloat16,
        device_map=resolved_device_map
    )

    def preprocess(dataset):
        preprocessor = Preprocessor(
            model_name=model_name,
            tokenizer=tokenizer,
            language_map=model_info["language_map"],
            max_source_length=max_source_length,
            max_target_length=max_target_length,
            restrict_source_language=model_info.get("restrict_source_language")
        )
        processed = dataset.map(preprocessor, remove_columns=dataset.column_names, load_from_cache_file=False)
        processed = processed.filter(
            lambda x: "input_ids" in x and "labels" in x and x["labels"] is not None and len(x["labels"]) > 0,
            load_from_cache_file=False
        )
        return processed

    dataset_processed = {
        "train": preprocess(train_dataset),
        "eval": preprocess(eval_dataset)
    }

    if len(dataset_processed["train"]) == 0:
        raise ValueError(f"No training examples remaining after preprocessing for model {model_name}")
    if len(dataset_processed["eval"]) == 0:
        raise ValueError(f"No evaluation examples remaining after preprocessing for model {model_name}")

    setup_logging(output_directory)

    _, base_model = load_tokenizer_and_model(
        model_info["model_id"],
        use_qlora=use_qlora,
        use_bfloat16=use_bfloat16,
        device_map=resolved_device_map
    )

    names = ["q", "k", "v", "o", "q_proj", "k_proj", "v_proj", "o_proj", "in_proj_weight"]
    detected = [n for n in names if
                any(hasattr(m, n) or n in type(m).__name__.lower() for _, m in base_model.named_modules())]
    lora_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        bias="none",
        task_type="SEQ_2_SEQ_LM",
        target_modules=list(set(detected)) or None
    )

    peft_model = get_peft_model(base_model, lora_config)
    peft_model.train()
    peft_model.print_trainable_parameters()

    steps_per_epoch = math.ceil(len(dataset_processed["train"]) / (batch_size * gradient_accumulation))
    logging.info(
        f"sizes | train={len(dataset_processed['train'])} eval={len(dataset_processed['eval'])} steps/epoch≈{steps_per_epoch}"
    )

    trainer = build_trainer(
        model_name=model_name,
        tokenizer=tokenizer,
        model=peft_model,
        dataset_processed=dataset_processed,
        output_directory=output_directory,
        learning_rate=learning_rate,
        batch_size=batch_size,
        gradient_accumulation=gradient_accumulation,
        epochs=epochs,
        max_steps=max_steps,
        eval_steps=eval_steps,
        logging_steps=logging_steps,
        save_steps=save_steps,
        use_bfloat16=use_bfloat16,
        use_fp16=use_fp16,
        seed=seed,
        warmup_ratio=warmup_ratio,
        disable_tqdm=disable_tqdm,
        use_qlora=use_qlora
    )

    train_result = trainer.train()

    peft_model.save_pretrained(os.path.join(output_directory, "lora"))
    tokenizer.save_pretrained(output_directory)

    with open(os.path.join(output_directory, "finished.json"), "w", encoding="utf-8") as f:
        json.dump({"status": "ok"}, f)

    logging.info(f"Fine-tuning complete. Model saved to {output_directory}")

    return trainer, train_result

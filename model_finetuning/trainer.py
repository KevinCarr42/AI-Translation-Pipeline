import os
from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments, DataCollatorForSeq2Seq

from model_finetuning.preprocessing import M2MDataCollator


def is_distributed():
    return int(os.environ.get("WORLD_SIZE", 1)) > 1


def build_trainer(model_name, tokenizer, model, dataset_processed, output_directory, learning_rate, batch_size, gradient_accumulation, epochs, max_steps, eval_steps, logging_steps, save_steps,
                  use_bfloat16, use_fp16, seed, warmup_ratio, disable_tqdm, use_qlora):
    if model_name == "m2m100_418m":
        data_collator = M2MDataCollator(tokenizer, model)
    else:
        data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)
    
    use_gradient_checkpointing = use_qlora
    
    training_args = Seq2SeqTrainingArguments(
        output_dir=output_directory,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation,
        learning_rate=learning_rate,
        num_train_epochs=0.0 if max_steps else epochs,
        max_steps=max_steps if max_steps else -1,
        eval_strategy="steps",
        eval_steps=eval_steps,
        logging_steps=logging_steps,
        save_steps=save_steps,
        save_total_limit=3,
        predict_with_generate=False,
        report_to=["none"],
        bf16=use_bfloat16,
        fp16=use_fp16 and not use_bfloat16,
        seed=seed,
        warmup_ratio=warmup_ratio,
        gradient_checkpointing=use_gradient_checkpointing,
        label_smoothing_factor=0.1,
        dataloader_num_workers=2,
        disable_tqdm=disable_tqdm,
        lr_scheduler_type="linear",
        weight_decay=0.01,
        ddp_find_unused_parameters=False if is_distributed() else None,
        label_names=["labels"],
    )
    
    try:
        trainer = Seq2SeqTrainer(
            model=model,
            args=training_args,
            train_dataset=dataset_processed["train"],
            eval_dataset=dataset_processed["eval"],
            processing_class=tokenizer,
            data_collator=data_collator,
        )
    except TypeError:
        trainer = Seq2SeqTrainer(
            model=model,
            args=training_args,
            train_dataset=dataset_processed["train"],
            eval_dataset=dataset_processed["eval"],
            tokenizer=tokenizer,
            data_collator=data_collator,
        )
    
    return trainer

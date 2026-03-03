import os, torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from peft import PeftModel
import config


def merge_one(base_model_id, lora_dir, out_dir, dtype=torch.bfloat16):
    tok = AutoTokenizer.from_pretrained(base_model_id, use_fast=True)
    if getattr(tok, "pad_token", None) is None and getattr(tok, "eos_token", None): tok.pad_token = tok.eos_token
    base = AutoModelForSeq2SeqLM.from_pretrained(base_model_id, torch_dtype=dtype, trust_remote_code=True)
    if hasattr(base.config, "vocab_size") and len(tok) > base.config.vocab_size:
        base.resize_token_embeddings(len(tok), mean_resizing=False)
    peft = PeftModel.from_pretrained(base, lora_dir)
    merged = peft.merge_and_unload()
    os.makedirs(out_dir, exist_ok=True)
    merged.save_pretrained(out_dir)
    tok.save_pretrained(out_dir)


def merge_weights():
    for name, cfg in config.MODELS.items():
        print(f'\nmerging {name}')
        lora_dir = os.path.join(config.MODEL_OUTPUT_DIR, name, "lora")
        out_dir = os.path.join(config.MERGED_MODEL_DIR, name)
        merge_one(cfg["model_id"], lora_dir, out_dir)

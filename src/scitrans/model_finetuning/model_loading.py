import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, BitsAndBytesConfig


def load_tokenizer_and_model(model_id, use_qlora, use_bfloat16, device_map):
    tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=True)
    if getattr(tokenizer, "pad_token", None) is None and getattr(tokenizer, "eos_token", None):
        tokenizer.pad_token = tokenizer.eos_token
    
    model_kwargs = {
        "torch_dtype": torch.bfloat16 if use_bfloat16 else torch.float16,
        "trust_remote_code": True
    }
    
    if use_qlora:
        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if use_bfloat16 else torch.float16
        )
    
    is_opus_model = "opus-mt" in model_id.lower() or "helsinki" in model_id.lower()
    if device_map is not None and not is_opus_model:
        model_kwargs["device_map"] = device_map
    
    model = AutoModelForSeq2SeqLM.from_pretrained(model_id, **model_kwargs)
    if hasattr(model.config, "vocab_size") and len(tokenizer) > model.config.vocab_size:
        model.resize_token_embeddings(len(tokenizer), mean_resizing=False)
    model.config.use_cache = False
    
    if use_qlora and hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
    
    return tokenizer, model

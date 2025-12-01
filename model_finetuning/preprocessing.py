import torch
from transformers import DataCollatorForSeq2Seq


class Preprocessor:
    def __init__(self, model_name, tokenizer, language_map, max_source_length, max_target_length, restrict_source_language=None):
        self.model_name = model_name
        self.tokenizer = tokenizer
        self.language_map = language_map
        self.max_source_length = max_source_length
        self.max_target_length = max_target_length
        self.restrict_source_language = restrict_source_language
    
    def _setup_tokenizer_languages(self, source_language, target_language):
        if not hasattr(self.tokenizer, 'src_lang'):
            return
        
        mapped_source = self.language_map.get(source_language, source_language)
        mapped_target = self.language_map.get(target_language, target_language)
        
        if self.model_name in ["m2m100_418m", "mbart50_mmt_fr", "mbart50_mmt_en"]:
            self.tokenizer.src_lang = mapped_source
            self.tokenizer.tgt_lang = mapped_target
    
    def __call__(self, example):
        if self.restrict_source_language and example["source_lang"] != self.restrict_source_language:
            return {}
        
        source_text = example["source"].strip()
        target_text = example["target"].strip()
        source_language = example["source_lang"]
        target_language = "en" if source_language == "fr" else "fr"
        
        if not target_text:
            return {}
        
        self._setup_tokenizer_languages(source_language, target_language)
        
        source_tokens = self.tokenizer(source_text, truncation=True, max_length=self.max_source_length)
        target_tokens = self.tokenizer(text_target=target_text, truncation=True, max_length=self.max_target_length)
        
        if not target_tokens.get("input_ids"):
            return {}
        
        source_tokens["labels"] = target_tokens["input_ids"]
        
        if self.model_name == "m2m100_418m":
            mapped_target = self.language_map[target_language]
            target_language_id = self.tokenizer.get_lang_id(mapped_target)
            pad_token_id = self.tokenizer.pad_token_id
            labels = source_tokens["labels"]
            
            decoder_input_ids = [target_language_id] + [
                (pad_token_id if token == -100 else token) for token in labels[:-1]
            ]
            source_tokens["decoder_input_ids"] = decoder_input_ids
        
        return source_tokens


class M2MDataCollator:
    def __init__(self, tokenizer, model, label_pad_token_id=-100):
        self.tokenizer = tokenizer
        self.label_pad_token_id = label_pad_token_id
        self.pad_collator = DataCollatorForSeq2Seq(tokenizer, model=model)
    
    def __call__(self, features):
        for f in features:
            f.pop("decoder_input_ids", None)
        
        batch = self.pad_collator(features)
        
        labels = batch["labels"]
        pad_id = self.tokenizer.pad_token_id
        labels_for_shift = torch.where(labels == -100, torch.tensor(pad_id, device=labels.device), labels)
        first_tok = labels_for_shift[:, :1]
        shifted = torch.cat([first_tok, labels_for_shift[:, :-1]], dim=1)
        batch["decoder_input_ids"] = shifted
        return batch

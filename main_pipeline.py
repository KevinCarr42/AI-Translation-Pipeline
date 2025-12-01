# TODO: consider doing this main pipeline completely differently

import os
import json
from datetime import datetime

import config
from data_cleaning import prepare_training_data
from model_finetuning import finetune_model
from preferential_translations import apply_preferential_translations, reverse_preferential_translations
from evaluation import test_translations_with_models, sample_evaluation_data


class PipelineOrchestrator:
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.execution_log = {
            'timestamp': datetime.now().isoformat(),
            'phases': {}
        }
    
    def log(self, message):
        if self.verbose:
            print(message)
    
    def run_phase_1_data_cleaning(self, output_pickle_prefix='pipeline_'):
        self.log("\n" + "=" * 80)
        self.log("PHASE 1: DATA CLEANING AND PREPROCESSING")
        self.log("=" * 80)
        
        phase_start = datetime.now()
        
        self.log(f"Starting data cleaning from: {config.PARSED_DOCS_DIR}")
        self.log(f"Output will be saved to: {config.DATA_DIR}")
        
        matched_data_df, correlations_df = prepare_training_data(
            output_pickle_prefix=output_pickle_prefix  # FIXME
        )
        
        phase_duration = (datetime.now() - phase_start).total_seconds()
        
        self.execution_log['phases']['data_cleaning'] = {
            'status': 'completed',
            'duration_seconds': phase_duration,
            'matched_rows': len(matched_data_df) if matched_data_df is not None else 0,
            'correlation_rows': len(correlations_df) if correlations_df is not None else 0,
        }
        
        self.log(f"Phase 1 completed in {phase_duration:.2f} seconds")
        return matched_data_df, correlations_df
    
    def run_phase_2_model_finetuning(self, model_name, data_path=None, epochs=None, use_qlora=True):
        self.log("\n" + "=" * 80)
        self.log(f"PHASE 2: MODEL FINE-TUNING ({model_name})")
        self.log("=" * 80)
        
        phase_start = datetime.now()
        
        if data_path is None:
            data_path = config.TRAINING_DATA_OUTPUT
        
        if epochs is None:
            epochs = config.TRAINING_HYPERPARAMS['epochs']
        
        output_dir = os.path.join(config.MODEL_OUTPUT_DIR, model_name)
        
        self.log(f"Fine-tuning model: {model_name}")
        self.log(f"Using data: {data_path}")
        self.log(f"Output directory: {output_dir}")
        
        trainer, train_result = finetune_model(
            model_name=model_name,
            data_path=data_path,
            output_directory=output_dir,
            learning_rate=config.TRAINING_HYPERPARAMS['learning_rate'],
            batch_size=config.TRAINING_HYPERPARAMS['batch_size'],
            gradient_accumulation=config.TRAINING_HYPERPARAMS['gradient_accumulation'],
            epochs=epochs,
            lora_r=config.TRAINING_HYPERPARAMS['lora_r'],
            lora_alpha=config.TRAINING_HYPERPARAMS['lora_alpha'],
            lora_dropout=config.TRAINING_HYPERPARAMS['lora_dropout'],
            use_qlora=use_qlora,
            use_bfloat16=config.QUANTIZATION_CONFIG['use_bfloat16'],
        )
        
        phase_duration = (datetime.now() - phase_start).total_seconds()
        
        self.execution_log['phases'][f'fine_tuning_{model_name}'] = {
            'status': 'completed',
            'duration_seconds': phase_duration,
            'training_loss': train_result.training_loss if train_result else None,
        }
        
        self.log(f"Phase 2 ({model_name}) completed in {phase_duration:.2f} seconds")
        return trainer, train_result
    
    def run_phase_3_preferential_translations(self, source_text, translations_file, source_language='en', target_language='fr'):
        self.log("\n" + "=" * 80)
        self.log("PHASE 3: PREFERENTIAL TRANSLATIONS")
        self.log("=" * 80)
        
        phase_start = datetime.now()
        
        self.log(f"Applying preferential translations")
        self.log(f"Source language: {source_language}, Target language: {target_language}")
        
        preprocessed_text, token_mapping = apply_preferential_translations(
            source_text=source_text,
            source_language=source_language,
            target_language=target_language,
            translations_file=translations_file,
            use_replacements=True,
            validate_tokens=True
        )
        
        phase_duration = (datetime.now() - phase_start).total_seconds()
        
        self.execution_log['phases']['preferential_translations'] = {
            'status': 'completed',
            'duration_seconds': phase_duration,
            'tokens_created': len(token_mapping) if token_mapping else 0,
        }
        
        self.log(f"Phase 3 completed in {phase_duration:.2f} seconds")
        self.log(f"Tokens created: {len(token_mapping) if token_mapping else 0}")
        
        return preprocessed_text, token_mapping
    
    def run_phase_4_evaluation(self, translation_manager, test_data_path=None, num_samples=10, output_dir=None):
        self.log("\n" + "=" * 80)
        self.log("PHASE 4: EVALUATION")
        self.log("=" * 80)
        
        phase_start = datetime.now()
        
        if test_data_path is None:
            test_data_path = config.TESTING_DATA_OUTPUT if hasattr(config, 'TESTING_DATA_OUTPUT') else None
        
        if output_dir is None:
            output_dir = os.path.join(config.DATA_DIR, 'evaluation_results')
        
        if test_data_path and os.path.exists(test_data_path):
            self.log(f"Loading evaluation data from: {test_data_path}")
            evaluation_data = sample_evaluation_data(test_data_path, num_samples=num_samples)
            
            csv_path, errors_path = test_translations_with_models(
                translation_manager=translation_manager,
                dataset=evaluation_data,
                output_directory=output_dir,
                test_name_suffix='comprehensive',
                use_find_replace=True
            )
            
            phase_duration = (datetime.now() - phase_start).total_seconds()
            
            self.execution_log['phases']['evaluation'] = {
                'status': 'completed',
                'duration_seconds': phase_duration,
                'samples_evaluated': len(evaluation_data),
                'results_path': csv_path,
                'errors_path': errors_path,
            }
            
            self.log(f"Phase 4 completed in {phase_duration:.2f} seconds")
        else:
            self.log("No evaluation data found. Skipping Phase 4.")
            self.execution_log['phases']['evaluation'] = {
                'status': 'skipped',
                'reason': 'No evaluation data file found',
            }
    
    def get_execution_summary(self):
        return self.execution_log
    
    def save_execution_log(self, output_path=None):
        if output_path is None:
            output_path = os.path.join(config.DATA_DIR, f"pipeline_execution_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        with open(output_path, 'w') as f:
            json.dump(self.execution_log, f, indent=2)
        
        self.log(f"\nExecution log saved to: {output_path}")
        return output_path


def create_orchestrator(verbose=True):
    return PipelineOrchestrator(verbose=verbose)


def run_full_pipeline(config_overrides=None):
    orchestrator = create_orchestrator(verbose=True)
    
    if config_overrides:
        for key, value in config_overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    orchestrator.log("=" * 80)
    orchestrator.log("PIPELINE ORCHESTRATOR - FULL EXECUTION")
    orchestrator.log("=" * 80)
    
    try:
        matched_data, correlations = orchestrator.run_phase_1_data_cleaning()
        
        for model_name in ['m2m100_418m', 'mbart50_mmt_fr', 'mbart50_mmt_en', 'opus_mt_en_fr', 'opus_mt_fr_en']:
            orchestrator.run_phase_2_model_finetuning(model_name)
        
        execution_summary = orchestrator.get_execution_summary()
        orchestrator.log("\n" + "=" * 80)
        orchestrator.log("PIPELINE EXECUTION SUMMARY")
        orchestrator.log("=" * 80)
        orchestrator.log(json.dumps(execution_summary, indent=2))
        
        orchestrator.save_execution_log()
        
        orchestrator.log("\nPipeline execution completed successfully!")
    
    except Exception as e:
        orchestrator.log(f"\nERROR during pipeline execution: {str(e)}")
        orchestrator.execution_log['error'] = str(e)
        orchestrator.save_execution_log()
        raise


if __name__ == "__main__":
    run_full_pipeline()

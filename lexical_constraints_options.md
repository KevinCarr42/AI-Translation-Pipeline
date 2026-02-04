# Lexical Constraints in AI Translation: Options and Considerations

This document outlines the current state of our translation pipeline's handling of lexical constraints (preferred translations for places, acronyms, technical terms, etc.) and explores potential solutions to known limitations.

## Table of Contents

1. [Current Architecture](#current-architecture)
2. [Identified Problems](#identified-problems)
3. [Previously Attempted Solutions](#previously-attempted-solutions)
4. [Proposed Options](#proposed-options)
5. [Additional Considerations](#additional-considerations)
6. [Evaluation Criteria](#evaluation-criteria)
7. [Recommended Path Forward](#recommended-path-forward)

---

## Current Architecture

### Overview

The translation pipeline uses a **token-replacement approach** with three stages:

1. **Preprocessing** (`rules_based_replacements/`): Replace English terminology with language-neutral tokens
   - Example: "Atlantic Cod" → `TAXON0012`
   - Tokens use format: `{CATEGORY}{COUNTER:04d}` (e.g., `NOMENCLATURE0001`, `ACRONYM0045`)
   - Categories: NOMENCLATURE, TAXON, ACRONYM, SITE (~350-400 terms total)

2. **Translation** (`translate/`): Model translates text containing tokens
   - Three model families: Opus-MT, M2M-100, mBART-50
   - Fine-tuned variants available in `../Data/finetuning_merged/`
   - Retry mechanism: up to 9 attempts with varying beam configurations
   - Validation: checks all tokens survived translation

3. **Postprocessing**: Replace tokens with French equivalents
   - Simple `str.replace()` substitution
   - Capitalization preservation (ALL_CAPS, lowercase, sentence-start)

4. **Model Selection**: Ensemble approach using cosine similarity
   - LaBSE embedder computes similarity between source and translation
   - Highest `similarity_vs_source` wins

5. **Fallback**: If tokens are corrupted after all retries, translate without constraints

### Data Sources

- **Terminology**: `../Data/preferential_translations.json`
- **Fine-tuned models**: `../Data/finetuning_merged/` (5 model variants)

---

## Identified Problems

### 1. No Gender Agreement Handling

**Severity: HIGH**

French has grammatical gender that affects articles and adjectives. The current system does not handle this.

**Example:**
- English: "a large Atlantic Cod"
- Token replacement: "a large TAXON0012"
- Model output: "un grand TAXON0012" (masculine agreement)
- Postprocess: "un grand Morue franche"
- **Problem**: "Morue" is feminine, should be "une grande Morue franche"

The terminology JSON contains no gender metadata, and no agreement rules are implemented.

### 2. No Plural Handling

**Severity: HIGH**

Plural forms are not tracked in the terminology dictionary.

**Example:**
- "Atlantic Cods" or "the Atlantic Cod population" may not match "Atlantic Cod"
- Even if matched, the French replacement may need plural agreement

### 3. Token Corruption During Translation

**Severity: MEDIUM**

Tokens sometimes get modified by the translation model:
- Spaces inserted: `NOMENCLATURE0001` → `NOMENCLATURE 0001`
- Pluralized: `NOMENCLATURE0001` → `NOMENCLATURE0001s`
- Partially dropped or merged with adjacent text

Current handling: fallback to translation without constraints (loses terminology control).

### 4. Partial Word Replacement Risk

**Severity: LOW-MEDIUM**

The preprocessing uses word boundary regex (`\b`), which should prevent partial matches. However:
- Postprocessing uses `str.replace()` which is global and not boundary-aware
- If a token appears multiple times (edge case), all instances are replaced
- Multi-word terms that share substrings with other terms could conflict

### 5. Similarity-Based Selection May Be Suboptimal

**Severity: MEDIUM**

The ensemble selection uses `similarity_vs_source` (how similar the translation is to the original English). This may:
- Favor overly literal translations over natural-sounding French
- Not correlate well with actual translation quality
- Ignore `similarity_vs_target` which is computed but unused

### 6. Capitalization Edge Cases

**Severity: LOW**

- Mixed case (CamelCase, Title Case) falls through without handling
- Multi-word terms at sentence start only capitalize the first letter of the first word
- Acronyms generally handled correctly

---

## Previously Attempted Solutions

| Approach | Result | Notes |
|----------|--------|-------|
| Lexical constraints as model parameter | Failed | Could not get `force_words_ids` or similar to work with our models |
| Pre-replacement (add French to English before translating) | Failed | Works in some language pairs but not EN→FR in our case |
| Fine-tuning for token replacement | Backfired | Models learned to output tokens without corresponding input tokens |
| Fine-tuning for pre-replacement | Failed | Did not produce usable results |
| Gender correction in find/replace | Abandoned | Caused partial word replacements (e.g., "available" → "availabla") |

---

## Proposed Options

### Option 1: Constrained Beam Search (Force Words)

**Approach**: Use Hugging Face's `force_words_ids` parameter to force specific token sequences in the output.

```python
force_words = [tokenizer.encode(french_term, add_special_tokens=False)
               for french_term in required_translations]
outputs = model.generate(inputs, force_words_ids=[force_words])
```

**Advantages:**
- Model sees real French words, not tokens
- Model can naturally handle gender/number agreement around forced words
- No postprocessing token replacement needed
- Native transformers feature

**Disadvantages:**
- Not all models support this well (may produce grammatically broken output)
- Can force impossible outputs if constraints conflict with context
- Requires careful tokenization (subword tokens must be handled)
- May significantly slow generation

**Implementation Effort**: Medium

**Risk Level**: Medium-High (may not work reliably)

---

### Option 2: LLM Proofreader with Direct Correction

**Approach**: Use a large language model (Claude, GPT-4, or local Mistral/Llama) as a post-translation correction step.

**Prompt Example:**
```
System: You are a French translation editor. Given a French translation and
terminology mappings, return ONLY the corrected translation with:
1. All terminology replaced with the specified French terms
2. Proper gender and number agreement applied
3. No other changes to the translation

User:
Translation: "Le rapport du DFO sur le Atlantic Cod montre un déclin."
Required terminology:
- "DFO" -> "MPO"
- "Atlantic Cod" -> "Morue franche" (feminine)

Assistant:
"Le rapport du MPO sur la Morue franche montre un déclin."
```

**Advantages:**
- LLMs handle French grammar naturally (gender, agreement, articles)
- Can handle complex cases the rule-based system cannot
- No changes needed to existing translation pipeline
- Can batch multiple sentences to reduce API calls
- Can use local models (Mistral, Llama) to avoid API costs

**Disadvantages:**
- Additional latency per translation
- API costs if using Claude/GPT-4 (can be mitigated with batching)
- Potential for hallucination or unwanted changes
- Adds another point of failure

**Implementation Effort**: Low-Medium

**Risk Level**: Low (additive, doesn't change existing pipeline)

**Cost Mitigation Strategies:**
- Batch 10-20 sentences per API call
- Use cheaper models (Claude Haiku, GPT-4o-mini) for correction tasks
- Cache corrections for repeated sentences
- Use local models for high-volume production

---

### Option 3: Instruction-Based Fine-Tuning

> **⚠️ Important**: This option requires **causal/autoregressive LLMs** (Llama, Mistral, Qwen, etc.), not seq2seq models. Our current models (Opus-MT, M2M-100, mBART-50) are encoder-decoder seq2seq models that don't understand natural language instructions—they're trained to map source text → target text, not to follow prompts. Attempting this with seq2seq models will likely result in the model trying to translate the instruction text itself or ignoring it entirely.

**Approach**: Fine-tune a causal LLM to follow explicit terminology instructions in the prompt.

**Training Data Format:**
```
Input: Translate to French. Use these exact terms:
- "Atlantic Cod" must become "Morue franche"
- "DFO" must become "MPO"

English: The DFO report on Atlantic Cod shows declining stocks.

Output: Le rapport du MPO sur la Morue franche montre un déclin des stocks.
```

**Key Differences from Previous Attempts:**
- Train on instruction + translation pairs, not token replacement
- Model learns to follow terminology instructions naturally
- Gender/number agreement handled implicitly by seeing correct examples

**Advantages:**
- Single model, no post-processing needed
- Model learns proper agreement from examples
- Eliminates token corruption issues
- Simpler production pipeline

**Disadvantages:**
- **Requires switching from seq2seq to causal LLM architecture**
- Requires significant training data with correct terminology usage
- May not generalize to unseen terminology
- Training and evaluation overhead
- Risk of catastrophic forgetting of general translation ability
- Causal LLMs are typically larger and slower than specialized translation models

**Implementation Effort**: High

**Risk Level**: Medium (previous fine-tuning attempts have failed)

**Dataset Requirements:**
- Need examples covering all ~350 terms
- Need examples with various grammatical contexts (gender, number, case)
- Need negative examples (what not to do)
- Estimate: 5,000-10,000 high-quality examples minimum

---

### Option 4: Fix Current Token System

**Approach**: Make targeted improvements to the existing token-replacement pipeline.

#### 4A. Improve Token Robustness in Postprocessing

Replace `str.replace()` with boundary-aware regex:

```python
# Current (problematic)
result_text = result_text.replace(token, replacement)

# Improved (boundary-aware)
import re
pattern = re.compile(r'\b' + re.escape(token) + r'\b')
result_text = pattern.sub(replacement, result_text)
```

#### 4B. Add Fuzzy Token Matching

Handle common token corruption patterns:

```python
def find_corrupted_token(text, token):
    # Handle space insertion: NOMENCLATURE0001 -> NOMENCLATURE 0001
    spaced = token[:len(token)//2] + r'\s*' + token[len(token)//2:]

    # Handle pluralization: NOMENCLATURE0001 -> NOMENCLATURE0001s
    pluralized = token + r's?'

    pattern = re.compile(f'({spaced}|{pluralized})', re.IGNORECASE)
    return pattern.search(text)
```

#### 4C. Improve Model Selection

Use `similarity_vs_target` instead of `similarity_vs_source` when reference translations are available:

```python
# Current
if result["similarity_vs_source"] > best_similarity:
    best_result = result

# Improved (when target available)
if result["similarity_vs_target"] > best_similarity:
    best_result = result
```

#### 4D. Add Gender Metadata to Terminology

Extend JSON structure:

```json
{
  "taxon": {
    "Morue franche": {
      "en": "Atlantic Cod",
      "gender": "feminine",
      "plural": "Morues franches"
    }
  }
}
```

Then implement basic agreement rules for surrounding adjectives.

**Advantages:**
- Incremental improvements to working system
- Low risk of breaking existing functionality
- Can be implemented and tested independently

**Disadvantages:**
- Does not solve gender agreement comprehensively
- Complexity grows with each fix
- May not address root cause

**Implementation Effort**: Low (4A, 4B, 4C) to High (4D)

**Risk Level**: Low

---

### Option 5: Hybrid Two-Stage Approach

**Approach**: Separate translation quality from terminology compliance.

**Stage 1: Natural Translation**
- Translate without any constraints
- Let model produce fluent, natural French

**Stage 2: Terminology Alignment**
- Compare translation against terminology list
- Identify mismatched terms
- Use small LLM to fix only the mismatched terms with proper agreement

**Example:**
```
Stage 1 Output: "Le rapport du Ministère sur la morue de l'Atlantique..."
Terminology Check: "morue de l'Atlantique" should be "Morue franche"
Stage 2 Fix: "Le rapport du MPO sur la Morue franche..."
```

**Advantages:**
- Clean separation of concerns
- Translation model optimized for fluency
- Correction model optimized for terminology
- Can use different models for each stage

**Disadvantages:**
- Two-stage pipeline adds complexity
- Terminology detection must be robust
- May introduce inconsistencies if not carefully implemented

**Implementation Effort**: Medium

**Risk Level**: Low-Medium

---

### Option 6: Neural Machine Translation with Terminology Injection

**Approach**: Use specialized NMT techniques designed for terminology constraints.

**Techniques to Investigate:**

1. **Inline Annotation**: Embed terminology in special markup
   ```
   Input: The <term en="DFO" fr="MPO">DFO</term> report...
   ```

2. **Soft Constraints**: Add terminology embeddings to encoder
   - Concatenate term embeddings with sentence embeddings
   - Model learns to attend to required terms

3. **Copy Mechanism**: Train model to copy certain tokens unchanged
   - Similar to pointer networks
   - Useful for proper nouns and acronyms

4. **Terminology-Aware Attention**: Modify attention to favor terminology spans

**Advantages:**
- Native integration with translation model
- No post-processing needed
- Can handle complex cases

**Disadvantages:**
- Requires significant model architecture changes
- May need to train from scratch
- Academic approaches may not transfer to production

**Implementation Effort**: Very High

**Risk Level**: High (research-level complexity)

---

## Additional Considerations

### Model Architecture Constraints

Understanding the difference between model types is critical for choosing an approach:

| Model Type | Examples | Instruction Following | Translation Quality |
|------------|----------|----------------------|---------------------|
| **Seq2seq (Encoder-Decoder)** | Opus-MT, M2M-100, mBART-50 | ❌ No | ✅ Excellent (specialized) |
| **Causal LLM (Decoder-only)** | Llama, Mistral, GPT, Claude | ✅ Yes | ⚠️ Good but general-purpose |

**Our current models are seq2seq.** This means:
- Options 1, 4, 5, 6 are compatible with current architecture
- Options 2, 3 require adding a causal LLM (either as API or local deployment)

**If switching to causal LLMs for translation:**
- Larger models (7B+ parameters) needed for good translation quality
- Slower inference than specialized seq2seq models
- More flexible (can do translation + instruction following in one model)
- Examples: Llama 3, Mistral, Qwen2 all have decent multilingual translation

### Cost Analysis

| Option | API Cost | Compute Cost | Development Cost |
|--------|----------|--------------|------------------|
| 1. Force Words | None | Same | Medium |
| 2. LLM Proofreader | $0.01-0.10/doc | Low | Low |
| 3. Instruction Fine-tuning | None | High (training) | High |
| 4. Fix Token System | None | Same | Low-Medium |
| 5. Hybrid Two-Stage | $0.005-0.05/doc | Medium | Medium |
| 6. NMT Injection | None | Very High | Very High |

### Latency Impact

| Option | Additional Latency |
|--------|-------------------|
| 1. Force Words | +20-50% (slower beam search) |
| 2. LLM Proofreader | +500-2000ms per batch |
| 3. Instruction Fine-tuning | None |
| 4. Fix Token System | Negligible |
| 5. Hybrid Two-Stage | +200-1000ms |
| 6. NMT Injection | None after training |

### Maintenance Burden

| Option | Ongoing Maintenance |
|--------|---------------------|
| 1. Force Words | Low |
| 2. LLM Proofreader | Low (prompt updates) |
| 3. Instruction Fine-tuning | High (retraining for new terms) |
| 4. Fix Token System | Medium (rule updates) |
| 5. Hybrid Two-Stage | Medium |
| 6. NMT Injection | Very High |

### Scalability

- Options 1, 3, 4, 6 scale well (no per-request API costs)
- Options 2, 5 have linear cost scaling with volume
- Local LLM deployment can mitigate API costs for Options 2, 5

### Domain-Specific Considerations

**Scientific Terminology:**
- Many terms have standardized translations (species names, chemical compounds)
- Gender often determined by word ending in French
- Abbreviations may or may not change between languages

**Geographic Names:**
- Proper nouns require special handling
- Some translate (Mount -> Mont), others don't
- Capitalization rules differ between EN/FR

**Government/Institutional Terms:**
- Acronyms often have official translations (DFO -> MPO)
- Some organizations have different names in each language
- Legal requirement for correct terminology in official documents

---

## Evaluation Criteria

When comparing options, consider:

1. **Terminology Accuracy**: % of required terms correctly translated
2. **Gender Agreement**: % of feminine/masculine terms with correct agreement
3. **Plural Handling**: % of plural forms correctly handled
4. **Fluency**: Human evaluation of translation naturalness
5. **Latency**: Time to translate a typical document
6. **Cost**: Per-document or per-word cost
7. **Reliability**: Failure rate, fallback frequency
8. **Maintainability**: Effort to add new terminology

### Suggested Evaluation Dataset

Create a test set with:
- 100 sentences containing terminology from each category
- 50 sentences with gender-sensitive contexts
- 50 sentences with plural forms
- 50 sentences with multiple terminology terms
- Human reference translations for comparison

---

## Recommended Path Forward

### Short-Term (1-2 weeks)

**Implement Option 4A and 4B**: Fix token robustness issues
- Low risk, immediate improvement
- Reduces fallback rate
- No architectural changes

### Medium-Term (2-4 weeks)

**Implement Option 2**: LLM Proofreader
- Add as optional post-processing step
- Start with Claude Haiku or GPT-4o-mini for cost efficiency
- Batch sentences to minimize API calls
- A/B test against current pipeline

### Long-Term Investigation

**Evaluate Option 3**: Instruction-based fine-tuning
- Build high-quality training dataset with terminology examples
- Test on small scale before full commitment
- Consider as replacement for token system if successful

### Decision Matrix

| If you need... | Recommended Option | Model Requirement |
|----------------|-------------------|-------------------|
| Quick win, minimal risk | Option 4 (Fix Token System) | Current seq2seq ✅ |
| Best quality, cost acceptable | Option 2 (LLM Proofreader) | + Causal LLM (API or local) |
| No ongoing API costs, keep seq2seq | Option 4 + Option 5 hybrid | Current seq2seq ✅ |
| No ongoing API costs, can switch models | Option 3 (Instruction Fine-tuning) | Causal LLM (local) |
| Simplest single-model architecture | Option 3 (if it works) | Causal LLM (local) |
| Research investment | Option 6 (NMT Injection) | Custom seq2seq |

---

## Questions for Team Discussion

1. What is the acceptable error rate for terminology compliance?
2. What is the budget for API costs per document?
3. How often is new terminology added to the dictionary?
4. Is latency a critical concern for this application?
5. Do we have resources for training data creation?
6. Should we prioritize gender agreement over other issues?
7. What is the timeline for improvements?
8. Are we open to switching from seq2seq models to causal LLMs for translation?
9. Do we have GPU resources to run local LLMs (7B+ parameters) if needed?

---

## Appendix: Code Locations

| Component | File Path |
|-----------|-----------|
| Translation models | `translate/models.py` |
| Token replacement | `rules_based_replacements/replacements.py` |
| Token utilities | `rules_based_replacements/token_utils.py` |
| Terminology JSON | `../Data/preferential_translations.json` |
| Fine-tuned models | `../Data/finetuning_merged/` |
| Model configuration | `translate/config.py` |

# Translation Evaluation Module Guide

This guide describes how to build a translation evaluation module that verifies terminology consistency between source and translated text—without modifying either. It checks whether expected terminology appears correctly in translations and can optionally use NLP to reduce false positives.

## Overview

### Purpose
Evaluate translation quality by checking:
1. When a source term from your terminology dictionary appears in the source text
2. Whether the corresponding target term appears in the translation
3. Optionally, whether the target term is used with correct part-of-speech/context

### Key Principle
This module is **read-only**—it analyzes and reports, but never modifies text. It's designed to work alongside your existing pipeline or as a post-hoc quality check.

---

## Module Structure

```
translate/
├── evaluation/
│   ├── __init__.py
│   ├── terminology_checker.py    # Core evaluation logic
│   ├── nlp_analyzer.py           # Optional NLP verification
│   └── report.py                 # Report generation
```

---

## Step 1: Core Terminology Checker

Create `translate/evaluation/terminology_checker.py`:

```python
"""
Terminology consistency checker for translations.

Verifies that terminology from a dictionary is correctly translated,
without modifying source or target text.
"""

import re
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class MatchStatus(Enum):
    """Status of a terminology match check."""
    FOUND = "found"                    # Target term found in translation
    MISSING = "missing"                # Target term not found
    PARTIAL = "partial"                # Partial match (e.g., wrong form)
    POS_MISMATCH = "pos_mismatch"      # Found but wrong part of speech
    UNCHECKED = "unchecked"            # NLP check skipped


@dataclass
class TermMatch:
    """Represents a source term found in the text."""
    source_term: str
    expected_target: str
    category: str
    source_position: Tuple[int, int]  # (start, end) in source text
    source_context: str               # Surrounding text for debugging


@dataclass 
class EvaluationResult:
    """Result of checking a single terminology match."""
    source_term: str
    expected_target: str
    category: str
    status: MatchStatus
    found_variant: Optional[str] = None      # What was actually found (if partial)
    target_position: Optional[Tuple[int, int]] = None
    target_context: Optional[str] = None
    pos_expected: Optional[str] = None       # Expected part of speech
    pos_found: Optional[str] = None          # Actual part of speech
    notes: str = ""


@dataclass
class TranslationEvaluation:
    """Complete evaluation of a source/translation pair."""
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    results: List[EvaluationResult] = field(default_factory=list)
    
    @property
    def total_terms(self) -> int:
        return len(self.results)
    
    @property
    def found_count(self) -> int:
        return sum(1 for r in self.results if r.status == MatchStatus.FOUND)
    
    @property
    def missing_count(self) -> int:
        return sum(1 for r in self.results if r.status == MatchStatus.MISSING)
    
    @property
    def partial_count(self) -> int:
        return sum(1 for r in self.results if r.status == MatchStatus.PARTIAL)
    
    @property
    def accuracy(self) -> float:
        if self.total_terms == 0:
            return 1.0
        return self.found_count / self.total_terms
    
    def get_issues(self) -> List[EvaluationResult]:
        """Return only results that indicate problems."""
        return [r for r in self.results 
                if r.status in (MatchStatus.MISSING, MatchStatus.PARTIAL, MatchStatus.POS_MISMATCH)]


class TerminologyChecker:
    """
    Checks translations for terminology consistency.
    
    Args:
        terminology_path: Path to JSON terminology file
        use_nlp: Whether to use NLP for part-of-speech verification
        nlp_analyzer: Optional NLP analyzer instance (created if use_nlp=True and not provided)
    """
    
    def __init__(self, terminology_path: str, use_nlp: bool = False, 
                 nlp_analyzer=None):
        self.use_nlp = use_nlp
        self.nlp_analyzer = nlp_analyzer
        
        # Load terminology
        self.terminology = self._load_terminology(terminology_path)
        
        # Build search patterns (longest first to avoid partial matches)
        self.patterns = self._build_patterns()
        
        # Initialize NLP if requested
        if self.use_nlp and self.nlp_analyzer is None:
            from translate.evaluation.nlp_analyzer import NLPAnalyzer
            self.nlp_analyzer = NLPAnalyzer()
    
    def _load_terminology(self, path: str) -> Dict:
        """Load terminology from JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Support both flat and nested formats
        if 'translations' in data:
            return data['translations']
        return data
    
    def _build_patterns(self) -> Dict[str, List[Tuple[re.Pattern, str, str]]]:
        """
        Build regex patterns for each category.
        
        Returns dict mapping category -> list of (pattern, source_term, target_term)
        """
        patterns = {}
        
        for category, terms in self.terminology.items():
            category_patterns = []
            
            # Sort by length (longest first)
            sorted_terms = sorted(terms.items(), key=lambda x: len(x[0]), reverse=True)
            
            for source_term, target_term in sorted_terms:
                # Use word boundaries for single words, exact match for phrases
                if ' ' in source_term:
                    pattern = re.compile(re.escape(source_term), re.IGNORECASE)
                else:
                    pattern = re.compile(r'\b' + re.escape(source_term) + r'\b', re.IGNORECASE)
                
                category_patterns.append((pattern, source_term, target_term))
            
            patterns[category] = category_patterns
        
        return patterns
    
    def _get_context(self, text: str, start: int, end: int, window: int = 30) -> str:
        """Extract surrounding context for a match."""
        ctx_start = max(0, start - window)
        ctx_end = min(len(text), end + window)
        
        prefix = "..." if ctx_start > 0 else ""
        suffix = "..." if ctx_end < len(text) else ""
        
        return f"{prefix}{text[ctx_start:ctx_end]}{suffix}"
    
    def find_source_terms(self, source_text: str, source_lang: str, 
                          target_lang: str) -> List[TermMatch]:
        """
        Find all terminology matches in source text.
        
        Args:
            source_text: The original text
            source_lang: Source language code ('en' or 'fr')
            target_lang: Target language code
            
        Returns:
            List of TermMatch objects for each found term
        """
        matches = []
        matched_spans = set()  # Avoid overlapping matches
        
        for category, category_patterns in self.patterns.items():
            for pattern, source_term, target_term in category_patterns:
                for match in pattern.finditer(source_text):
                    start, end = match.span()
                    
                    # Skip if this span overlaps with an existing match
                    if any(start < e and end > s for s, e in matched_spans):
                        continue
                    
                    matched_spans.add((start, end))
                    
                    matches.append(TermMatch(
                        source_term=match.group(),  # Preserve original case
                        expected_target=target_term,
                        category=category,
                        source_position=(start, end),
                        source_context=self._get_context(source_text, start, end)
                    ))
        
        return matches
    
    def check_target_term(self, translated_text: str, expected_target: str,
                          source_term: str, category: str) -> EvaluationResult:
        """
        Check if expected target term appears in translation.
        
        Args:
            translated_text: The translated text
            expected_target: The term we expect to find
            source_term: Original source term (for reporting)
            category: Terminology category
            
        Returns:
            EvaluationResult with match status
        """
        # Build pattern for target term
        if ' ' in expected_target:
            pattern = re.compile(re.escape(expected_target), re.IGNORECASE)
        else:
            pattern = re.compile(r'\b' + re.escape(expected_target) + r'\b', re.IGNORECASE)
        
        match = pattern.search(translated_text)
        
        if match:
            start, end = match.span()
            return EvaluationResult(
                source_term=source_term,
                expected_target=expected_target,
                category=category,
                status=MatchStatus.FOUND,
                found_variant=match.group(),
                target_position=(start, end),
                target_context=self._get_context(translated_text, start, end)
            )
        
        # Check for partial matches (e.g., found "table" but expected "la table")
        partial_result = self._check_partial_match(translated_text, expected_target, 
                                                    source_term, category)
        if partial_result:
            return partial_result
        
        # Not found at all
        return EvaluationResult(
            source_term=source_term,
            expected_target=expected_target,
            category=category,
            status=MatchStatus.MISSING,
            notes="Expected term not found in translation"
        )
    
    def _check_partial_match(self, translated_text: str, expected_target: str,
                              source_term: str, category: str) -> Optional[EvaluationResult]:
        """
        Check for partial matches when exact match fails.
        
        For example, if expected "la table" but found "table" or "une table".
        """
        # Extract the core term (without articles for French)
        articles = ['le ', 'la ', "l'", 'les ', 'un ', 'une ', 'des ', 
                    'the ', 'a ', 'an ']
        
        core_target = expected_target
        for article in articles:
            if expected_target.lower().startswith(article):
                core_target = expected_target[len(article):]
                break
        
        # Search for core term
        if ' ' in core_target:
            pattern = re.compile(re.escape(core_target), re.IGNORECASE)
        else:
            pattern = re.compile(r'\b' + re.escape(core_target) + r'\b', re.IGNORECASE)
        
        match = pattern.search(translated_text)
        
        if match:
            start, end = match.span()
            # Check what actually precedes the match
            prefix_start = max(0, start - 10)
            actual_context = translated_text[prefix_start:end]
            
            return EvaluationResult(
                source_term=source_term,
                expected_target=expected_target,
                category=category,
                status=MatchStatus.PARTIAL,
                found_variant=actual_context.strip(),
                target_position=(start, end),
                target_context=self._get_context(translated_text, start, end),
                notes=f"Found '{match.group()}' but expected '{expected_target}'"
            )
        
        return None
    
    def evaluate(self, source_text: str, translated_text: str,
                 source_lang: str = "en", target_lang: str = "fr") -> TranslationEvaluation:
        """
        Evaluate a translation for terminology consistency.
        
        Args:
            source_text: Original text
            translated_text: Translated text
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            TranslationEvaluation with all results
        """
        evaluation = TranslationEvaluation(
            source_text=source_text,
            translated_text=translated_text,
            source_lang=source_lang,
            target_lang=target_lang
        )
        
        # Find all source terms
        source_matches = self.find_source_terms(source_text, source_lang, target_lang)
        
        # Check each term in translation
        for term_match in source_matches:
            result = self.check_target_term(
                translated_text,
                term_match.expected_target,
                term_match.source_term,
                term_match.category
            )
            
            # Optional NLP verification
            if self.use_nlp and result.status == MatchStatus.FOUND:
                result = self._verify_with_nlp(result, translated_text, target_lang)
            
            evaluation.results.append(result)
        
        return evaluation
    
    def _verify_with_nlp(self, result: EvaluationResult, translated_text: str,
                         target_lang: str) -> EvaluationResult:
        """
        Use NLP to verify the matched term is used correctly.
        
        Checks part-of-speech to catch cases like:
        - Noun used as verb
        - Wrong grammatical form
        """
        if self.nlp_analyzer is None:
            result.notes += " (NLP verification skipped - no analyzer)"
            return result
        
        try:
            pos_info = self.nlp_analyzer.get_pos_in_context(
                translated_text, 
                result.target_position,
                target_lang
            )
            
            if pos_info:
                result.pos_found = pos_info.get('pos')
                result.pos_expected = pos_info.get('expected_pos')
                
                if pos_info.get('is_valid') is False:
                    result.status = MatchStatus.POS_MISMATCH
                    result.notes = f"POS mismatch: expected {result.pos_expected}, found {result.pos_found}"
        
        except Exception as e:
            result.notes += f" (NLP error: {str(e)})"
        
        return result
    
    def evaluate_batch(self, pairs: List[Tuple[str, str]], 
                       source_lang: str = "en",
                       target_lang: str = "fr") -> List[TranslationEvaluation]:
        """
        Evaluate multiple source/translation pairs.
        
        Args:
            pairs: List of (source_text, translated_text) tuples
            
        Returns:
            List of TranslationEvaluation objects
        """
        return [
            self.evaluate(source, translated, source_lang, target_lang)
            for source, translated in pairs
        ]
```

---

## Step 2: Optional NLP Analyzer

Create `translate/evaluation/nlp_analyzer.py`:

```python
"""
NLP-based verification for translation evaluation.

Uses spaCy for part-of-speech tagging to verify terminology
is used in the correct grammatical context.
"""

from typing import Dict, Optional, Tuple


class NLPAnalyzer:
    """
    Analyzes text using spaCy for grammatical verification.
    
    This is optional—the checker works without it, but NLP
    can reduce false positives by catching incorrect usage.
    
    Potential issues NLP can catch:
    - "table" used as verb ("to table a motion") vs noun
    - Wrong grammatical number (singular vs plural)
    - Adjective vs noun confusion
    
    Potential issues where NLP might backfire:
    - Domain-specific terms with unusual POS
    - Proper nouns misidentified
    - Rare or technical vocabulary not in spaCy's model
    """
    
    # Expected POS for common terminology categories
    CATEGORY_POS_MAP = {
        'nomenclature': ['NOUN', 'PROPN'],
        'taxon': ['NOUN', 'PROPN'],
        'acronym': ['NOUN', 'PROPN'],
        'site': ['NOUN', 'PROPN'],
        'species': ['NOUN', 'PROPN'],
        'organization': ['NOUN', 'PROPN'],
        'technical': ['NOUN', 'ADJ'],
    }
    
    def __init__(self, models: Optional[Dict[str, str]] = None):
        """
        Initialize NLP analyzer with spaCy models.
        
        Args:
            models: Dict mapping language codes to spaCy model names.
                    Defaults to small models for en/fr.
        """
        self.models = models or {
            'en': 'en_core_web_sm',
            'fr': 'fr_core_news_sm'
        }
        self._nlp_cache = {}
    
    def _get_nlp(self, lang: str):
        """Load spaCy model for language (cached)."""
        if lang not in self._nlp_cache:
            try:
                import spacy
                model_name = self.models.get(lang)
                if model_name is None:
                    raise ValueError(f"No spaCy model configured for language: {lang}")
                self._nlp_cache[lang] = spacy.load(model_name)
            except OSError:
                # Model not installed
                raise RuntimeError(
                    f"spaCy model '{model_name}' not found. "
                    f"Install with: python -m spacy download {model_name}"
                )
        return self._nlp_cache[lang]
    
    def get_pos_in_context(self, text: str, position: Tuple[int, int],
                           lang: str, category: Optional[str] = None) -> Dict:
        """
        Get part-of-speech information for text at a specific position.
        
        Args:
            text: Full text
            position: (start, end) character positions of the term
            lang: Language code
            category: Optional terminology category for expected POS lookup
            
        Returns:
            Dict with 'pos', 'expected_pos', 'is_valid', 'token_text'
        """
        nlp = self._get_nlp(lang)
        doc = nlp(text)
        
        start, end = position
        
        # Find tokens that overlap with the position
        matching_tokens = []
        for token in doc:
            token_start = token.idx
            token_end = token.idx + len(token.text)
            
            # Check for overlap
            if token_start < end and token_end > start:
                matching_tokens.append(token)
        
        if not matching_tokens:
            return {
                'pos': None,
                'expected_pos': None,
                'is_valid': None,
                'token_text': None,
                'error': 'No tokens found at position'
            }
        
        # Use the POS of the head noun/main token
        # For multi-word terms, find the noun
        main_token = matching_tokens[0]
        for token in matching_tokens:
            if token.pos_ in ('NOUN', 'PROPN'):
                main_token = token
                break
        
        found_pos = main_token.pos_
        expected_pos = None
        is_valid = True
        
        if category:
            expected_pos_list = self.CATEGORY_POS_MAP.get(category.lower(), ['NOUN', 'PROPN'])
            expected_pos = expected_pos_list
            is_valid = found_pos in expected_pos_list
        
        return {
            'pos': found_pos,
            'expected_pos': expected_pos,
            'is_valid': is_valid,
            'token_text': main_token.text,
            'lemma': main_token.lemma_,
            'dep': main_token.dep_
        }
    
    def check_agreement(self, text: str, term_position: Tuple[int, int],
                        lang: str) -> Dict:
        """
        Check grammatical agreement for French terms.
        
        Verifies that articles/adjectives agree with noun gender/number.
        
        Args:
            text: Full text
            term_position: Position of the term to check
            lang: Language code
            
        Returns:
            Dict with agreement analysis
        """
        if lang != 'fr':
            return {'checked': False, 'reason': 'Agreement check only for French'}
        
        nlp = self._get_nlp(lang)
        doc = nlp(text)
        
        start, end = term_position
        
        # Find the main noun
        noun_token = None
        for token in doc:
            if token.idx >= start and token.idx < end:
                if token.pos_ in ('NOUN', 'PROPN'):
                    noun_token = token
                    break
        
        if not noun_token:
            return {'checked': False, 'reason': 'No noun found at position'}
        
        # Get morphological features
        noun_morph = noun_token.morph.to_dict()
        noun_gender = noun_morph.get('Gender')
        noun_number = noun_morph.get('Number')
        
        # Check preceding determiner/adjective
        issues = []
        for token in doc:
            if token.head == noun_token and token.dep_ in ('det', 'amod'):
                token_morph = token.morph.to_dict()
                token_gender = token_morph.get('Gender')
                token_number = token_morph.get('Number')
                
                if token_gender and noun_gender and token_gender != noun_gender:
                    issues.append(f"Gender mismatch: '{token.text}' ({token_gender}) with '{noun_token.text}' ({noun_gender})")
                
                if token_number and noun_number and token_number != noun_number:
                    issues.append(f"Number mismatch: '{token.text}' ({token_number}) with '{noun_token.text}' ({noun_number})")
        
        return {
            'checked': True,
            'noun': noun_token.text,
            'gender': noun_gender,
            'number': noun_number,
            'agreement_issues': issues,
            'is_valid': len(issues) == 0
        }
```

---

## Step 3: Report Generation

Create `translate/evaluation/report.py`:

```python
"""
Report generation for translation evaluation results.
"""

import json
from typing import List, Optional
from dataclasses import asdict
from translate.evaluation.terminology_checker import TranslationEvaluation, MatchStatus


def generate_summary(evaluations: List[TranslationEvaluation]) -> dict:
    """
    Generate summary statistics for a batch of evaluations.
    """
    total_terms = sum(e.total_terms for e in evaluations)
    total_found = sum(e.found_count for e in evaluations)
    total_missing = sum(e.missing_count for e in evaluations)
    total_partial = sum(e.partial_count for e in evaluations)
    
    sentences_with_issues = sum(1 for e in evaluations if e.missing_count > 0 or e.partial_count > 0)
    
    return {
        'total_sentences': len(evaluations),
        'sentences_with_issues': sentences_with_issues,
        'total_terms_checked': total_terms,
        'terms_found': total_found,
        'terms_missing': total_missing,
        'terms_partial': total_partial,
        'overall_accuracy': total_found / total_terms if total_terms > 0 else 1.0,
        'issue_rate': sentences_with_issues / len(evaluations) if evaluations else 0.0
    }


def generate_detailed_report(evaluations: List[TranslationEvaluation],
                              include_successful: bool = False) -> str:
    """
    Generate a human-readable detailed report.
    
    Args:
        evaluations: List of evaluation results
        include_successful: Whether to include successful matches (verbose)
        
    Returns:
        Formatted string report
    """
    lines = []
    lines.append("=" * 70)
    lines.append("TRANSLATION TERMINOLOGY EVALUATION REPORT")
    lines.append("=" * 70)
    lines.append("")
    
    # Summary
    summary = generate_summary(evaluations)
    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(f"Sentences evaluated:     {summary['total_sentences']}")
    lines.append(f"Sentences with issues:   {summary['sentences_with_issues']}")
    lines.append(f"Terms checked:           {summary['total_terms_checked']}")
    lines.append(f"Terms found correctly:   {summary['terms_found']}")
    lines.append(f"Terms missing:           {summary['terms_missing']}")
    lines.append(f"Terms partial match:     {summary['terms_partial']}")
    lines.append(f"Overall accuracy:        {summary['overall_accuracy']:.1%}")
    lines.append("")
    
    # Detailed issues
    lines.append("DETAILED ISSUES")
    lines.append("-" * 40)
    
    issue_count = 0
    for i, evaluation in enumerate(evaluations):
        issues = evaluation.get_issues()
        
        if not issues and not include_successful:
            continue
        
        results_to_show = issues if not include_successful else evaluation.results
        
        if results_to_show:
            issue_count += 1
            lines.append(f"\n[Sentence {i + 1}]")
            lines.append(f"Source: {evaluation.source_text[:100]}{'...' if len(evaluation.source_text) > 100 else ''}")
            lines.append(f"Translation: {evaluation.translated_text[:100]}{'...' if len(evaluation.translated_text) > 100 else ''}")
            
            for result in results_to_show:
                status_icon = {
                    MatchStatus.FOUND: "✓",
                    MatchStatus.MISSING: "✗",
                    MatchStatus.PARTIAL: "~",
                    MatchStatus.POS_MISMATCH: "⚠"
                }.get(result.status, "?")
                
                lines.append(f"  {status_icon} '{result.source_term}' → expected '{result.expected_target}'")
                
                if result.status == MatchStatus.PARTIAL:
                    lines.append(f"    Found variant: '{result.found_variant}'")
                
                if result.notes:
                    lines.append(f"    Note: {result.notes}")
    
    if issue_count == 0:
        lines.append("No issues found!")
    
    lines.append("")
    lines.append("=" * 70)
    
    return "\n".join(lines)


def generate_json_report(evaluations: List[TranslationEvaluation],
                         include_successful: bool = True) -> str:
    """
    Generate JSON report for programmatic processing.
    """
    def evaluation_to_dict(e: TranslationEvaluation) -> dict:
        return {
            'source_text': e.source_text,
            'translated_text': e.translated_text,
            'source_lang': e.source_lang,
            'target_lang': e.target_lang,
            'total_terms': e.total_terms,
            'accuracy': e.accuracy,
            'results': [
                {
                    'source_term': r.source_term,
                    'expected_target': r.expected_target,
                    'category': r.category,
                    'status': r.status.value,
                    'found_variant': r.found_variant,
                    'notes': r.notes
                }
                for r in e.results
                if include_successful or r.status != MatchStatus.FOUND
            ]
        }
    
    report = {
        'summary': generate_summary(evaluations),
        'evaluations': [evaluation_to_dict(e) for e in evaluations]
    }
    
    return json.dumps(report, indent=2, ensure_ascii=False)


def generate_csv_issues(evaluations: List[TranslationEvaluation]) -> str:
    """
    Generate CSV of issues for spreadsheet analysis.
    """
    lines = ["sentence_idx,source_term,expected_target,category,status,found_variant,notes"]
    
    for i, evaluation in enumerate(evaluations):
        for result in evaluation.get_issues():
            # Escape commas and quotes in text fields
            def escape(s):
                if s is None:
                    return ""
                s = str(s).replace('"', '""')
                if ',' in s or '"' in s or '\n' in s:
                    return f'"{s}"'
                return s
            
            lines.append(",".join([
                str(i + 1),
                escape(result.source_term),
                escape(result.expected_target),
                escape(result.category),
                result.status.value,
                escape(result.found_variant),
                escape(result.notes)
            ]))
    
    return "\n".join(lines)
```

---

## Step 4: Convenience Interface

Create `translate/evaluation/__init__.py`:

```python
"""
Translation evaluation module.

Provides tools for checking terminology consistency in translations.
"""

from translate.evaluation.terminology_checker import (
    TerminologyChecker,
    TranslationEvaluation,
    EvaluationResult,
    MatchStatus,
    TermMatch
)

from translate.evaluation.report import (
    generate_summary,
    generate_detailed_report,
    generate_json_report,
    generate_csv_issues
)


def evaluate_translation(source_text: str, translated_text: str,
                         terminology_path: str, source_lang: str = "en",
                         target_lang: str = "fr", use_nlp: bool = False) -> TranslationEvaluation:
    """
    Convenience function to evaluate a single translation.
    
    Args:
        source_text: Original text
        translated_text: Translated text  
        terminology_path: Path to terminology JSON
        source_lang: Source language code
        target_lang: Target language code
        use_nlp: Whether to use NLP verification (requires spaCy)
        
    Returns:
        TranslationEvaluation object with results
    """
    checker = TerminologyChecker(terminology_path, use_nlp=use_nlp)
    return checker.evaluate(source_text, translated_text, source_lang, target_lang)


def evaluate_file(source_file: str, translated_file: str,
                  terminology_path: str, source_lang: str = "en",
                  target_lang: str = "fr", use_nlp: bool = False,
                  output_format: str = "text") -> str:
    """
    Evaluate translations from parallel text files.
    
    Files should have one sentence per line, aligned.
    
    Args:
        source_file: Path to source text file
        translated_file: Path to translated text file
        terminology_path: Path to terminology JSON
        source_lang: Source language code
        target_lang: Target language code
        use_nlp: Whether to use NLP verification
        output_format: 'text', 'json', or 'csv'
        
    Returns:
        Formatted report string
    """
    with open(source_file, 'r', encoding='utf-8') as f:
        source_lines = f.readlines()
    
    with open(translated_file, 'r', encoding='utf-8') as f:
        translated_lines = f.readlines()
    
    if len(source_lines) != len(translated_lines):
        raise ValueError(
            f"File line count mismatch: {len(source_lines)} source lines, "
            f"{len(translated_lines)} translated lines"
        )
    
    pairs = [
        (s.strip(), t.strip()) 
        for s, t in zip(source_lines, translated_lines)
        if s.strip() and t.strip()
    ]
    
    checker = TerminologyChecker(terminology_path, use_nlp=use_nlp)
    evaluations = checker.evaluate_batch(pairs, source_lang, target_lang)
    
    if output_format == 'json':
        return generate_json_report(evaluations)
    elif output_format == 'csv':
        return generate_csv_issues(evaluations)
    else:
        return generate_detailed_report(evaluations)


__all__ = [
    'TerminologyChecker',
    'TranslationEvaluation', 
    'EvaluationResult',
    'MatchStatus',
    'TermMatch',
    'evaluate_translation',
    'evaluate_file',
    'generate_summary',
    'generate_detailed_report',
    'generate_json_report',
    'generate_csv_issues'
]
```

---

## Usage Examples

### Basic Usage

```python
from translate.evaluation import evaluate_translation

result = evaluate_translation(
    source_text="The table is in the laboratory.",
    translated_text="Le table est dans le laboratoire.",  # Wrong article!
    terminology_path="terminology.json",
    use_nlp=False
)

print(f"Accuracy: {result.accuracy:.0%}")
for issue in result.get_issues():
    print(f"  - Expected '{issue.expected_target}', got partial match")
```

### With NLP Verification

```python
from translate.evaluation import TerminologyChecker

# Enable NLP to catch part-of-speech errors
checker = TerminologyChecker(
    terminology_path="terminology.json",
    use_nlp=True
)

result = checker.evaluate(
    source_text="We need to table this discussion.",  # "table" as verb
    translated_text="Nous devons mettre cette discussion sur la table.",
    source_lang="en",
    target_lang="fr"
)

# NLP might flag this since "table" is used as verb in source
# but "la table" (noun) appears in translation
```

### Batch Evaluation with Report

```python
from translate.evaluation import TerminologyChecker, generate_detailed_report

checker = TerminologyChecker("terminology.json", use_nlp=False)

pairs = [
    ("The dog is here.", "Le chien est ici."),
    ("The table is broken.", "Le table est cassée."),  # Wrong article
    ("Meeting starts at noon.", "La réunion commence à midi."),
]

evaluations = checker.evaluate_batch(pairs)
report = generate_detailed_report(evaluations)
print(report)
```

### Integration with Your Pipeline

```python
from translate.document import translate_document
from translate.evaluation import TerminologyChecker, generate_detailed_report

# After translation
translate_document(
    input_text_file="source.txt",
    output_text_file="translated.txt",
    source_lang="en"
)

# Evaluate the results
from translate.evaluation import evaluate_file

report = evaluate_file(
    source_file="source.txt",
    translated_file="translated.txt",
    terminology_path="terminology.json",
    use_nlp=False,
    output_format="text"
)

print(report)

# Or save to file
with open("evaluation_report.txt", "w") as f:
    f.write(report)
```

---

## NLP: When to Use and Potential Issues

### When NLP Helps

| Scenario | Example | NLP Benefit |
|----------|---------|-------------|
| Verb vs Noun | "table" (verb) vs "table" (noun) | Catches incorrect POS |
| Homographs | "lead" (metal) vs "lead" (guide) | Context disambiguation |
| Agreement check | "le table" vs "la table" | Gender/number validation |

### When NLP Might Backfire

| Scenario | Problem | Recommendation |
|----------|---------|----------------|
| Domain terms | spaCy may not know "taxon" | Add to exceptions list |
| Proper nouns | May be tagged incorrectly | Trust terminology dict |
| Rare vocabulary | Model uncertainty | Lower confidence threshold |
| Multi-word terms | Tokenization splits term | Use phrase-level check |

### Configuration for Your Domain

```python
class NLPAnalyzer:
    # Add your domain-specific categories
    CATEGORY_POS_MAP = {
        'nomenclature': ['NOUN', 'PROPN'],
        'taxon': ['NOUN', 'PROPN'],
        'acronym': ['NOUN', 'PROPN', 'X'],  # X for unknown
        'site': ['NOUN', 'PROPN'],
        # Add your categories...
    }
```

---

## Terminology File Format

The evaluation module expects the same format as your existing `preferential_translations`:

```json
{
  "nomenclature": {
    "source_term": "target_term",
    "table": "la table",
    "dog": "le chien"
  },
  "taxon": {
    "Canis lupus": "Canis lupus",
    "Homo sapiens": "Homo sapiens"
  },
  "acronym": {
    "DNA": "ADN",
    "RNA": "ARN"
  }
}
```

Or the flat format:

```json
{
  "en_to_fr": {
    "table": "la table",
    "dog": "le chien"
  }
}
```

---

## Dependencies

**Required:**
- Python 3.8+
- (No external dependencies for basic functionality)

**Optional (for NLP features):**
```bash
pip install spacy
python -m spacy download en_core_web_sm
python -m spacy download fr_core_news_sm
```

---

## Testing Checklist

- [ ] Basic evaluation without NLP
- [ ] Evaluation with NLP enabled
- [ ] Handling missing terms
- [ ] Handling partial matches (wrong article)
- [ ] Multi-word term detection
- [ ] Case-insensitive matching
- [ ] Batch evaluation
- [ ] Report generation (text, JSON, CSV)
- [ ] File-based evaluation
- [ ] Integration with translation pipeline

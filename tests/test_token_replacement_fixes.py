import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rules_based_replacements.replacements import find_corrupted_token, postprocess_translation


def test_find_corrupted_token():
    print("\n=== Testing find_corrupted_token() ===\n")
    
    test_cases = [
        {
            'name': 'Exact match',
            'text': 'The NOMENCLATURE0001 is valid',
            'token': 'NOMENCLATURE0001',
            'expected': (True, 4, 'NOMENCLATURE0001')
        },
        {
            'name': 'Space-separated token',
            'text': 'The NOMENCLATURE 0001 is valid',
            'token': 'NOMENCLATURE0001',
            'expected': (True, 4, 'NOMENCLATURE 0001')
        },
        {
            'name': 'Pluralized token with s',
            'text': 'The NOMENCLATURE0001s are valid',
            'token': 'NOMENCLATURE0001',
            'expected': (True, 4, 'NOMENCLATURE0001s')
        },
        {
            'name': 'Pluralized token with es',
            'text': 'The NOMENCLATURE0001es are valid',
            'token': 'NOMENCLATURE0001',
            'expected': (True, 4, 'NOMENCLATURE0001es')
        },
        {
            'name': 'Token not found',
            'text': 'There is no token here',
            'token': 'NOMENCLATURE0001',
            'expected': (False, None, None)
        },
        {
            'name': 'Invalid token format but exact match exists',
            'text': 'The INVALIDTOKEN is here',
            'token': 'INVALIDTOKEN',
            'expected': (True, 4, 'INVALIDTOKEN')
        },
        {
            'name': 'Token at start of text',
            'text': 'NOMENCLATURE0001 is at the start',
            'token': 'NOMENCLATURE0001',
            'expected': (True, 0, 'NOMENCLATURE0001')
        },
        {
            'name': 'Multiple TAXON tokens',
            'text': 'The TAXON0005 and TAXON0010 are present',
            'token': 'TAXON0005',
            'expected': (True, 4, 'TAXON0005')
        },
        {
            'name': 'ACRONYM token with space',
            'text': 'The ACRONYM 0023 is here',
            'token': 'ACRONYM0023',
            'expected': (True, 4, 'ACRONYM 0023')
        },
        {
            'name': 'SITE token pluralized',
            'text': 'The SITE0042s are all valid',
            'token': 'SITE0042',
            'expected': (True, 4, 'SITE0042s')
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        result = find_corrupted_token(test['text'], test['token'])
        expected = test['expected']
        
        if result == expected:
            print(f"[PASS] {test['name']}")
            print(f"  Found: {result}")
            passed += 1
        else:
            print(f"[FAIL] {test['name']}")
            print(f"  Expected: {expected}")
            print(f"  Got:      {result}")
            failed += 1
    
    print(f"\n{passed} passed, {failed} failed\n")
    return failed == 0


def test_postprocess_translation():
    print("\n=== Testing postprocess_translation() ===\n")
    
    test_cases = [
        {
            'name': 'Clean token replacement',
            'translated_text': 'The NOMENCLATURE0001 is valid',
            'token_mapping': {
                'NOMENCLATURE0001': {
                    'original_text': 'carbon dioxide',
                    'translation': 'dioxyde de carbone',
                    'should_translate': True
                }
            },
            'expected': 'The dioxyde de carbone is valid'
        },
        {
            'name': 'Space-separated token recovery',
            'translated_text': 'The NOMENCLATURE 0001 is valid',
            'token_mapping': {
                'NOMENCLATURE0001': {
                    'original_text': 'carbon dioxide',
                    'translation': 'dioxyde de carbone',
                    'should_translate': True
                }
            },
            'expected': 'The dioxyde de carbone is valid'
        },
        {
            'name': 'Pluralized token recovery',
            'translated_text': 'The NOMENCLATURE0001s are valid',
            'token_mapping': {
                'NOMENCLATURE0001': {
                    'original_text': 'carbon dioxide',
                    'translation': 'dioxyde de carbone',
                    'should_translate': True
                }
            },
            'expected': 'The dioxyde de carbone are valid'
        },
        {
            'name': 'No translation (preserve original)',
            'translated_text': 'The NOMENCLATURE0001 is valid',
            'token_mapping': {
                'NOMENCLATURE0001': {
                    'original_text': 'carbon dioxide',
                    'translation': 'None',
                    'should_translate': False
                }
            },
            'expected': 'The carbon dioxide is valid'
        },
        {
            'name': 'Multiple tokens (clean)',
            'translated_text': 'TAXON0001 and NOMENCLATURE0002 are here',
            'token_mapping': {
                'TAXON0001': {
                    'original_text': 'Escherichia coli',
                    'translation': 'Escherichia coli',
                    'should_translate': True
                },
                'NOMENCLATURE0002': {
                    'original_text': 'oxygen',
                    'translation': 'oxygène',
                    'should_translate': True
                }
            },
            'expected': 'Escherichia coli and oxygène are here'
        },
        {
            'name': 'Multiple tokens (mixed corruptions)',
            'translated_text': 'TAXON 0001 and NOMENCLATURE0002s are here',
            'token_mapping': {
                'TAXON0001': {
                    'original_text': 'Escherichia coli',
                    'translation': 'Escherichia coli',
                    'should_translate': True
                },
                'NOMENCLATURE0002': {
                    'original_text': 'oxygen',
                    'translation': 'oxygène',
                    'should_translate': True
                }
            },
            'expected': 'Escherichia coli and oxygène are here'
        },
        {
            'name': 'Boundary-aware (not partial match)',
            'translated_text': 'The NOMENCLATURE0001 word',
            'token_mapping': {
                'NOMENCLATURE0001': {
                    'original_text': 'test',
                    'translation': 'essai',
                    'should_translate': True
                }
            },
            'expected': 'The essai word'
        },
        {
            'name': 'Sentence start capitalization',
            'translated_text': 'NOMENCLATURE0001 is at the start',
            'token_mapping': {
                'NOMENCLATURE0001': {
                    'original_text': 'oxygen',
                    'translation': 'oxygène',
                    'should_translate': True
                }
            },
            'expected': 'Oxygène is at the start'
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        result = postprocess_translation(test['translated_text'], test['token_mapping'])
        expected = test['expected']
        
        if result == expected:
            print(f"[PASS] {test['name']}")
            print(f"  Result: {result}")
            passed += 1
        else:
            print(f"[FAIL] {test['name']}")
            print(f"  Input:    {test['translated_text']}")
            print(f"  Expected: {expected}")
            print(f"  Got:      {result}")
            failed += 1
    
    print(f"\n{passed} passed, {failed} failed\n")
    return failed == 0


def test_validation_with_fuzzy_matching():
    print("\n=== Testing is_valid_translation() with fuzzy matching ===\n")
    
    from translate.models import TranslationManager
    
    manager = TranslationManager(all_models={})
    
    test_cases = [
        {
            'name': 'Clean tokens pass',
            'translated_text': 'The NOMENCLATURE0001 and TAXON0005 are valid',
            'original_text': 'Original text with NOMENCLATURE0001 and TAXON0005',
            'token_mapping': {
                'NOMENCLATURE0001': {},
                'TAXON0005': {}
            },
            'expected': True
        },
        {
            'name': 'Space-separated tokens pass',
            'translated_text': 'The NOMENCLATURE 0001 and TAXON 0005 are valid',
            'original_text': 'Original text with NOMENCLATURE0001 and TAXON0005',
            'token_mapping': {
                'NOMENCLATURE0001': {},
                'TAXON0005': {}
            },
            'expected': True
        },
        {
            'name': 'Pluralized tokens pass',
            'translated_text': 'The NOMENCLATURE0001s and TAXON0005es are valid',
            'original_text': 'Original text with NOMENCLATURE0001 and TAXON0005',
            'token_mapping': {
                'NOMENCLATURE0001': {},
                'TAXON0005': {}
            },
            'expected': True
        },
        {
            'name': 'Mixed clean and corrupted pass',
            'translated_text': 'The NOMENCLATURE0001 and TAXON 0005 are valid',
            'original_text': 'Original text with NOMENCLATURE0001 and TAXON0005',
            'token_mapping': {
                'NOMENCLATURE0001': {},
                'TAXON0005': {}
            },
            'expected': True
        },
        {
            'name': 'Missing token fails',
            'translated_text': 'The NOMENCLATURE0001 is here',
            'original_text': 'Original text with NOMENCLATURE0001',
            'token_mapping': {
                'NOMENCLATURE0001': {},
                'TAXON0005': {}
            },
            'expected': False
        },
        {
            'name': 'No token mapping passes',
            'translated_text': 'Any text without tokens',
            'original_text': 'Original text',
            'token_mapping': None,
            'expected': True
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        result = manager.is_valid_translation(
            test['translated_text'],
            test['original_text'],
            test['token_mapping']
        )
        expected = test['expected']
        
        if result == expected:
            print(f"[PASS] {test['name']}")
            print(f"  Valid: {result}")
            passed += 1
        else:
            print(f"[FAIL] {test['name']}")
            print(f"  Text: {test['translated_text']}")
            print(f"  Tokens: {list(test['token_mapping'].keys()) if test['token_mapping'] else 'None'}")
            print(f"  Expected: {expected}")
            print(f"  Got:      {result}")
            failed += 1
    
    print(f"\n{passed} passed, {failed} failed\n")
    return failed == 0


def test_mbart50_bug_fix():
    print("\n=== Verifying MBART50 bug fix ===\n")
    
    import re
    
    models_file = os.path.join(os.path.dirname(__file__), '..', 'translate', 'models.py')
    
    with open(models_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    bug_pattern = r'generation_arguments\.update\(generation_arguments\)'
    correct_pattern = r'generation_arguments\.update\(generation_kwargs\)'
    
    has_bug = re.search(bug_pattern, content)
    has_fix = re.search(correct_pattern, content)
    
    if has_bug:
        print("[FAIL] Self-update bug still present in models.py")
        print("  Found: generation_arguments.update(generation_arguments)")
        return False
    elif has_fix:
        print("[PASS] Bug is fixed")
        print("  Found correct pattern: generation_arguments.update(generation_kwargs)")
        return True
    else:
        print("[UNCLEAR] Could not find either pattern in models.py")
        return False


def run_all_tests():
    print("\n" + "=" * 60)
    print("  Token Replacement Fixes - Test Suite")
    print("=" * 60)
    
    results = {
        'find_corrupted_token': test_find_corrupted_token(),
        'postprocess_translation': test_postprocess_translation(),
        'validation_with_fuzzy_matching': test_validation_with_fuzzy_matching(),
        'mbart50_bug_fix': test_mbart50_bug_fix()
    }
    
    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    
    total = len(results)
    passed = sum(results.values())
    
    for test_name, success in results.items():
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} test suites passed")
    
    if passed == total:
        print("\n*** All tests passed! The fixes are working correctly. ***")
        return 0
    else:
        print(f"\n*** {total - passed} test suite(s) failed. ***")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)

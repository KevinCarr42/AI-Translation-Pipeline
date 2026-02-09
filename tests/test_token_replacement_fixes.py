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
    assert failed == 0, f"{failed} test cases failed"


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
    assert failed == 0, f"{failed} test cases failed"


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
    assert failed == 0, f"{failed} test cases failed"


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
        assert False, "Self-update bug still present"
    elif has_fix:
        print("[PASS] Bug is fixed")
        print("  Found correct pattern: generation_arguments.update(generation_kwargs)")
    else:
        print("[UNCLEAR] Could not find either pattern in models.py")
        assert False, "Could not find either pattern in models.py"


def test_name_token_not_translated():
    print("\n=== Testing NAME token with should_translate=False ===\n")
    
    test_cases = [
        {
            'name': 'Person name restored to original',
            'translated_text': 'Dr. NAME0001 conducted the research',
            'token_mapping': {
                'NAME0001': {
                    'original_text': 'Jennifer Smith',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                }
            },
            'expected': 'Dr. Jennifer Smith conducted the research'
        },
        {
            'name': 'Multiple person names restored',
            'translated_text': 'NAME0001 and NAME0002 collaborated on the study',
            'token_mapping': {
                'NAME0001': {
                    'original_text': 'Dr. Michael Chen',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                },
                'NAME0002': {
                    'original_text': 'Sarah Johnson',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                }
            },
            'expected': 'Dr. Michael Chen and Sarah Johnson collaborated on the study'
        },
        {
            'name': 'Name with should_translate=False ignores translation field',
            'translated_text': 'The researcher NAME0001 published findings',
            'token_mapping': {
                'NAME0001': {
                    'original_text': 'Robert Williams',
                    'category': 'name',
                    'translation': 'This should be ignored',
                    'should_translate': False
                }
            },
            'expected': 'The researcher Robert Williams published findings'
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
    assert failed == 0, f"{failed} test cases failed"


def test_name_token_sentence_start_verbatim():
    print("\n=== Testing NAME token at sentence start ===\n")
    
    test_cases = [
        {
            'name': 'Name at text start restored verbatim',
            'translated_text': 'NAME0001 conducted the research',
            'token_mapping': {
                'NAME0001': {
                    'original_text': 'Jennifer Smith',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                }
            },
            'expected': 'Jennifer Smith conducted the research'
        },
        {
            'name': 'Name at sentence start after period restored verbatim',
            'translated_text': 'The study was successful. NAME0001 presented the findings',
            'token_mapping': {
                'NAME0001': {
                    'original_text': 'Dr. Chen',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                }
            },
            'expected': 'The study was successful. Dr. Chen presented the findings'
        },
        {
            'name': 'Name at sentence start after exclamation restored verbatim',
            'translated_text': 'Amazing results! NAME0001 achieved a breakthrough',
            'token_mapping': {
                'NAME0001': {
                    'original_text': 'Maria Rodriguez',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                }
            },
            'expected': 'Amazing results! Maria Rodriguez achieved a breakthrough'
        },
        {
            'name': 'Name at sentence start after question restored verbatim',
            'translated_text': 'Who led the research? NAME0001 was the principal investigator',
            'token_mapping': {
                'NAME0001': {
                    'original_text': 'James Brown',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                }
            },
            'expected': 'Who led the research? James Brown was the principal investigator'
        },
        {
            'name': 'Lowercase name at sentence start preserved lowercase',
            'translated_text': 'NAME0001 is a historical figure',
            'token_mapping': {
                'NAME0001': {
                    'original_text': 'van Gogh',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                }
            },
            'expected': 'van Gogh is a historical figure'
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
    assert failed == 0, f"{failed} test cases failed"


def test_corrupted_name_token_recovery():
    print("\n=== Testing corrupted NAME token recovery ===\n")
    
    test_cases = [
        {
            'name': 'Space-separated NAME token',
            'translated_text': 'Dr. NAME 0001 conducted the research',
            'token_mapping': {
                'NAME0001': {
                    'original_text': 'Jennifer Smith',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                }
            },
            'expected': 'Dr. Jennifer Smith conducted the research'
        },
        {
            'name': 'Pluralized NAME token with s',
            'translated_text': 'The NAME0001s family contributed to science',
            'token_mapping': {
                'NAME0001': {
                    'original_text': 'Smith',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                }
            },
            'expected': 'The Smith family contributed to science'
        },
        {
            'name': 'Pluralized NAME token with es',
            'translated_text': 'The NAME0001es dynasty ruled the region',
            'token_mapping': {
                'NAME0001': {
                    'original_text': 'Jones',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                }
            },
            'expected': 'The Jones dynasty ruled the region'
        },
        {
            'name': 'Multiple corrupted NAME tokens',
            'translated_text': 'NAME 0001 and NAME0002s worked together',
            'token_mapping': {
                'NAME0001': {
                    'original_text': 'Dr. Chen',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                },
                'NAME0002': {
                    'original_text': 'Johnson',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                }
            },
            'expected': 'Dr. Chen and Johnson worked together'
        },
        {
            'name': 'Corrupted NAME at sentence start',
            'translated_text': 'NAME 0001 was a pioneer in the field',
            'token_mapping': {
                'NAME0001': {
                    'original_text': 'Maria Curie',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                }
            },
            'expected': 'Maria Curie was a pioneer in the field'
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
    assert failed == 0, f"{failed} test cases failed"


def test_integration_name_and_nomenclature():
    print("\n=== Testing integration of NAME and NOMENCLATURE tokens ===\n")
    
    test_cases = [
        {
            'name': 'NAME and NOMENCLATURE both preserved correctly',
            'translated_text': 'NAME0001 studied NOMENCLATURE0001 in the laboratory',
            'token_mapping': {
                'NAME0001': {
                    'original_text': 'Dr. Jennifer Smith',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                },
                'NOMENCLATURE0001': {
                    'original_text': 'carbon dioxide',
                    'category': 'nomenclature',
                    'translation': 'dioxyde de carbone',
                    'should_translate': True
                }
            },
            'expected': 'Dr. Jennifer Smith studied dioxyde de carbone in the laboratory'
        },
        {
            'name': 'NAME and TAXON with mixed corruption',
            'translated_text': 'NAME 0001 discovered TAXON0001s in the region',
            'token_mapping': {
                'NAME0001': {
                    'original_text': 'Dr. Michael Chen',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                },
                'TAXON0001': {
                    'original_text': 'Escherichia coli',
                    'category': 'taxon',
                    'translation': 'Escherichia coli',
                    'should_translate': True
                }
            },
            'expected': 'Dr. Michael Chen discovered Escherichia coli in the region'
        },
        {
            'name': 'Multiple NAMEs and NOMENCLATURE at sentence start',
            'translated_text': 'NAME0001 and NAME0002 analyzed NOMENCLATURE0001. NOMENCLATURE0002 was also examined',
            'token_mapping': {
                'NAME0001': {
                    'original_text': 'Sarah Johnson',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                },
                'NAME0002': {
                    'original_text': 'Robert Williams',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                },
                'NOMENCLATURE0001': {
                    'original_text': 'oxygen',
                    'category': 'nomenclature',
                    'translation': 'oxygène',
                    'should_translate': True
                },
                'NOMENCLATURE0002': {
                    'original_text': 'nitrogen',
                    'category': 'nomenclature',
                    'translation': 'azote',
                    'should_translate': True
                }
            },
            'expected': 'Sarah Johnson and Robert Williams analyzed oxygène. Azote was also examined'
        },
        {
            'name': 'NAME and ACRONYM with various corruptions',
            'translated_text': 'NAME 0001 worked with ACRONYM 0001 and NOMENCLATURE0001s',
            'token_mapping': {
                'NAME0001': {
                    'original_text': 'Dr. Maria Rodriguez',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                },
                'ACRONYM0001': {
                    'original_text': 'DNA',
                    'category': 'acronym',
                    'translation': 'ADN',
                    'should_translate': True
                },
                'NOMENCLATURE0001': {
                    'original_text': 'protein',
                    'category': 'nomenclature',
                    'translation': 'protéine',
                    'should_translate': True
                }
            },
            'expected': 'Dr. Maria Rodriguez worked with ADN and protéine'
        },
        {
            'name': 'NAME at start with NOMENCLATURE should_translate=False',
            'translated_text': 'NAME0001 preserved NOMENCLATURE0001 samples',
            'token_mapping': {
                'NAME0001': {
                    'original_text': 'James Brown',
                    'category': 'name',
                    'translation': None,
                    'should_translate': False
                },
                'NOMENCLATURE0001': {
                    'original_text': 'water',
                    'category': 'nomenclature',
                    'translation': 'eau',
                    'should_translate': False
                }
            },
            'expected': 'James Brown preserved water samples'
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
    assert failed == 0, f"{failed} test cases failed"

import re


def normalize_apostrophes(text):
    return text.replace("'", "'").replace("'", "'")


_PROTECTED_LABEL_PATTERN = re.compile(
    r'\b(?:Figure|Fig|Table|Tableau)\.?\s*\d+\.?', re.IGNORECASE
)
_PLACEHOLDER = '\x00'


def _split_into_sentences(text):
    protected_positions = []
    for match in _PROTECTED_LABEL_PATTERN.finditer(text):
        for i, ch in enumerate(match.group()):
            if ch == '.':
                protected_positions.append(match.start() + i)
    
    chars = list(text)
    for pos in protected_positions:
        chars[pos] = _PLACEHOLDER
    
    sentences = re.split(r'(?<=[.!?])\s+', ''.join(chars))
    return [s.replace(_PLACEHOLDER, '.') for s in sentences]

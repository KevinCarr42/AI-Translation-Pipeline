from dataclasses import dataclass


@dataclass(frozen=True)
class FormattedRun:
    text: str
    italic: bool = False
    superscript: bool = False
    subscript: bool = False


def parse_formatted_string(s):
    results = []
    i = 0
    while i < len(s):
        char = s[i]
        if char in ('/', '_', '^'):
            marker = char
            i += 1
            is_braced = i < len(s) and s[i] == '{'
            
            if is_braced:
                start = i + 1
                count = 1
                j = start
                while j < len(s) and count > 0:
                    if s[j] == '{':
                        count += 1
                    elif s[j] == '}':
                        count -= 1
                    j += 1
                inner = s[start:j - 1]
                i = j
            else:
                start = i
                while i < len(s) and s[i] not in ('/', '_', '^', ' ', '}', '{'):
                    i += 1
                inner = s[start:i]
                if marker == '/' and i < len(s) and s[i] == '/':
                    i += 1
            
            nested = parse_formatted_string(inner)
            for run in nested:
                results.append(FormattedRun(
                    text=run.text,
                    italic=run.italic or marker == '/',
                    superscript=run.superscript or marker == '^',
                    subscript=run.subscript or marker == '_'
                ))
        else:
            start = i
            while i < len(s) and s[i] not in ('/', '_', '^'):
                i += 1
            results.append(FormattedRun(text=s[start:i]))
    return results

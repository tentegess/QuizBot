import math

CHAR_MAP = {
    '0': 8.67,
    '1': 5,
    '2': 7.47,
    '3': 7.18,
    '4': 8.25,
    '5': 7.38,
    '6': 7.9,
    '7': 7.38,
    '8': 7.95,
    '9': 7.9,
    'a': 6.98,
    'ą': 6.98,
    'b': 7.45,
    'c': 6.53,
    'ć': 6.53,
    'd': 7.53,
    'e': 6.98,
    'ę': 6.98,
    'f': 4.35,
    'g': 7.05,
    'h': 7.38,
    'i': 3.4,
    'j': 3.4,
    'k': 6.73,
    'l': 3.4,
    'm': 11.42,
    'n': 7.38,
    'o': 7.38,
    'ó': 7.38,
    'p': 7.53,
    'q': 7.45,
    'r': 5.02,
    's': 6.18,
    'ś': 6.18,
    't': 4.72,
    'u': 7.38,
    'v': 6.58,
    'w': 10.1,
    'x': 6.6,
    'y': 6.77,
    'z': 6.32,
    'ż': 6.32,
    'ź': 6.32,
    'A': 9.63,
    'Ą': 9.63,
    'B': 7.63,
    'C': 8.85,
    'Ć': 8.85,
    'D': 9.83,
    'E': 7.08,
    'Ę': 7.08,
    'F': 6.68,
    'G': 9.75,
    'H': 9.83,
    'I': 3.8,
    'J': 5.17,
    'K': 8.52,
    'L': 6.55,
    'M': 12.6,
    'N': 9.83,
    'O': 10.43,
    'Ó': 10.43,
    'P': 7.5,
    'Q': 10.43,
    'R': 7.98,
    'S': 7.17,
    'Ś': 7.17,
    'T': 8.4,
    'U': 9.65,
    'V': 9.47,
    'W': 14.23,
    'X': 8.9,
    'Y': 8.9,
    'Z': 8.33,
    'Ż': 8.33,
    'Ź': 8.33,
    '/': 7.5,
    '*': 5.6,
    '-': 4.95,
    ',': 3.17,
    '.': 3.17,
    '_': 6.35,
    '?': 7.25,
    '!': 3.8,
    '#': 9.25,
    '@': 11.7,
    '$': 7.38,
    '%': 12.6,
    '^': 6.35,
    '&': 9.53,
    '=': 8.25,
    '<': 8,
    '>': 8,
    '\\': 7.5,
    '|': 3.72,
    '"': 5.72,
    "'": 3.17,
    ';': 3.3,
    ':': 3.3,
    '{': 6.67,
    '}': 6.67,
    '[': 5.72,
    ']': 5.72,
    '(': 5.47,
    ')': 5.47,
    '': 6.35,
    '~': 5.72,
    ' ': 3.8,
    }

PAD_MAP = [
    ('　', 14),
    (' ', 4.65),
    (' ', 3.5),
    (' ', 1.87),
    (' ', 1.05)
]

def calc_string_width(string,char_map=CHAR_MAP):
    total = 0.0
    for char in string:
        total += char_map.get(char,6.7)
    return total

def pad_string(string,width):
    def _pad(_width, pad_map=PAD_MAP):
        result = ""
        remaining = _width
        for (char, char_w) in pad_map:
            if remaining < 0.5:
                break
            times = math.floor(remaining / char_w)
            if times > 0:
                result += char * times
                remaining -= (char_w * times)
        return result

    current_width = calc_string_width(string)
    if current_width >= width:
        return F"\u200b{string}\u200b"

    pad_width = (width-current_width)
    return f"\u200b{string}{_pad(pad_width)}\u200b"

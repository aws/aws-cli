import re


class RegexFilter(object):
    def __init__(self, pattern, replacement):
        self._pattern = pattern
        self._replacement = replacement
        self._regex = None

    def filter_text(self, text):
        regex = self._get_regex()
        filtered_text = regex.subn(self._replacement, text)
        return filtered_text[0]

    def _get_regex(self):
        if self._regex is None:
            self._regex = re.compile(self._pattern)
        return self._regex

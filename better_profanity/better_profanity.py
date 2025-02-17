# -*- coding: utf-8 -*-

from itertools import product
from .constants import ALLOWED_CHARACTERS

from .utils import (
    read_wordlist,
    get_replacement_for_swear_word,
    any_next_words_form_swear_word,
    get_complete_path_of_file,
)


class Profanity:
    def __init__(self):
        self.CENSOR_WORDSET = set()
        self.CHARS_MAPPING = {
            "a": ("a", "@", "*", "4",),
            "i": ("i", "*", "l", "1", "!",),
            "o": ("o", "*", "0", "@",),
            "u": ("u", "*", "v",),
            "v": ("v", "*", "u",),
            "l": ("l", "1", "!",),
            "e": ("e", "*", "3",),
            "s": ("s", "$", "5",),
            "t": ("t", "7",),
        }
        self.MAX_NUMBER_COMBINATIONS = 1
        self.ALLOWED_CHARACTERS = ALLOWED_CHARACTERS
        self._default_wordlist_filename = get_complete_path_of_file(
            "profanity_wordlist.txt"
        )
        self.load_censor_words()

    ## PUBLIC ##

    def censor(self, text, censor_char="*"):
        """Replace the swear words in the text with `censor_char`."""

        if not isinstance(text, str):
            text = str(text)
        if not isinstance(censor_char, str):
            censor_char = str(censor_char)

        if not self.CENSOR_WORDSET:
            self.load_censor_words()
        return self._swear_words_corrector(text, censor_char)

    def load_censor_words_from_file(self, filename, **kwargs):
        words = read_wordlist(filename)
        self._populate_words_to_wordset(words, **kwargs)

    def load_censor_words(self, custom_words=None, **kwargs):
        """Generate a set of words that need to be censored."""
        # Replace the words from `profanity_wordlist.txt` with a custom list
        custom_words = custom_words or read_wordlist(self._default_wordlist_filename)
        self._populate_words_to_wordset(custom_words, **kwargs)

    def add_censor_words(self, custom_words):
        if not isinstance(custom_words, (list, tuple, set)):
            raise TypeError(
                "Function 'add_censor_words' only accepts list, tuple or set."
            )
        # Convert all arguments to lower case. Works for tuples and lists too from re-casting into sets
        custom_words_combos = set()
        for word in custom_words:
            custom_words_combos.update(set(self._generate_patterns_from_word(word.lower())))
        self.CENSOR_WORDSET.update(custom_words_combos)

    def remove_censor_words(self, custom_words):
        if not isinstance(custom_words, (list, tuple, set)):
            raise TypeError(
                "Function 'remove_censor_words' only accepts list, tuple or set."
            )
        # The function assumes the input custom_words are all "regular" (i.e. not leetspeak derivatives) to assure
        # clean removal of interested words and all of their derivatives.
        # This function is not responsible for figuring out the base form of the banned word.
        custom_words_combos = set()
        for word in custom_words:
            custom_words_combos.update(set(self._generate_patterns_from_word(word.lower())))
        self.CENSOR_WORDSET.difference_update(custom_words_combos) # If word not in CENSOR_WORDSET fxn will skip

    def contains_what_profanity(self, text):
        """Return the first detected swear word of the input text and if not, it returns an empty string"""
        return self._swear_words_corrector(text, None)

    def contains_profanity(self, text):
        """Return True if the input text has any swear words."""
        return self.contains_what_profanity(text) != ""

    ## PRIVATE ##

    def _populate_words_to_wordset(self, words, *, whitelist_words=None):
        if whitelist_words is not None and not isinstance(
            whitelist_words, (list, set, tuple)
        ):
            raise TypeError(
                "The 'whitelist_words' keyword argument only accepts list, tuple or set."
            )

        # Validation
        whitelist_words = whitelist_words or []
        for index, word in enumerate(whitelist_words):
            if not isinstance(word, str):
                raise ValueError(
                    "Each word in 'whitelist_words' must be 'str' type, "
                    "but '{word}' found.".format(word=type(word))
                )
            whitelist_words[index] = word.lower()

        # Populate the words into an internal wordset
        whitelist_words = set(whitelist_words)
        all_censor_words = set()
        for word in words:
            # All words in CENSOR_WORDSET must be in lowercase
            word = word.lower()

            if word in whitelist_words:
                continue

            num_of_non_allowed_chars = self._count_non_allowed_characters(word)
            if num_of_non_allowed_chars > self.MAX_NUMBER_COMBINATIONS:
                self.MAX_NUMBER_COMBINATIONS = num_of_non_allowed_chars

            all_censor_words.update(set(self._generate_patterns_from_word(word)))

        # The default wordlist takes ~5MB+ of memory
        self.CENSOR_WORDSET = all_censor_words

    def _count_non_allowed_characters(self, word):
        count = 0
        for char in iter(word):
            if char not in self.ALLOWED_CHARACTERS:
                count += 1
        return count

    def _generate_patterns_from_word(self, word):
        """Return all patterns can be generated from the word."""
        combos = [
            (char,) if char not in self.CHARS_MAPPING else self.CHARS_MAPPING[char]
            for char in iter(word)
        ]
        return ("".join(pattern) for pattern in product(*combos))

    def _update_next_words_indices(self, text, words_indices, start_idx):
        """Return a list of next words_indices after the input index."""
        if not words_indices:
            words_indices = self._get_next_words(
                text, start_idx, self.MAX_NUMBER_COMBINATIONS
            )
        else:
            del words_indices[:2]
            if words_indices and words_indices[-1][0] != "":
                words_indices += self._get_next_words(text, words_indices[-1][1], 1)
        return words_indices

    def _swear_words_corrector(self, text, censor_char):
        """Replace the swear words with censor characters."""
        censored_text = ""
        cur_word = ""
        skip_index = -1
        next_words_indices = []
        start_idx_of_next_word = self._get_start_index_of_next_word(text, 0)

        # If there are no words in the text, return the raw text without parsing
        if start_idx_of_next_word >= len(text) - 1:
            return text

        # Left strip the text, to avoid inaccurate parsing
        if start_idx_of_next_word > 0:
            censored_text = text[:start_idx_of_next_word]
            text = text[start_idx_of_next_word:]

        # Splitting each word in the text to compare with censored words
        for index, char in iter(enumerate(text)):
            if index < skip_index:
                continue
            if char in ALLOWED_CHARACTERS:
                cur_word += char
                continue

            # Skip continuous non-allowed characters
            if cur_word.strip() == "":
                censored_text += char
                cur_word = ""
                continue

            # Iterate the next words combined with the current one
            # to check if it forms a swear word
            next_words_indices = self._update_next_words_indices(
                text, next_words_indices, index
            )
            swear_word_result, end_index = any_next_words_form_swear_word(
                cur_word, next_words_indices, self.CENSOR_WORDSET
            )
            # If censor_char is None, it implies whoever calls this function is only checking if swear words exists
            if swear_word_result != "":
                if censor_char is None:
                    return swear_word_result
                cur_word = get_replacement_for_swear_word(censor_char)
                skip_index = end_index
                char = ""
                next_words_indices = []

            # If the current a swear word
            if cur_word.lower() in self.CENSOR_WORDSET:
                if censor_char is None:
                    return cur_word
                cur_word = get_replacement_for_swear_word(censor_char)

            censored_text += cur_word + char
            cur_word = ""

        # Final check
        if cur_word != "" and skip_index < len(text) - 1:
            if cur_word.lower() in self.CENSOR_WORDSET:
                if censor_char is None:
                    return cur_word
                cur_word = get_replacement_for_swear_word(censor_char)
            censored_text += cur_word
        # If censor_char is None, it implies whoever calls this function is only checking if swear words exists
        if censor_char is None:
            return ""
        return censored_text

    def _get_start_index_of_next_word(self, text, start_idx):
        """Return the index of the first character of the next word in the given text."""
        start_idx_of_next_word = len(text)
        for index in iter(range(start_idx, len(text))):
            if text[index] not in self.ALLOWED_CHARACTERS:
                continue
            start_idx_of_next_word = index
            break

        return start_idx_of_next_word

    def _get_next_word_and_end_index(self, text, start_idx):
        """Return the next word in the given text, and the index of its last character."""
        next_word = ""
        index = start_idx
        for index in iter(range(start_idx, len(text))):
            char = text[index]
            if char in self.ALLOWED_CHARACTERS:
                next_word += char
                continue
            break
            # Breaks when the index points to a disallowed char (i.e. spacing char) immediately behind an allowed char
        if next_word != "" and start_idx == index:
            # Catch edge case where the last char of `text` is ONE allowed char preceded by spacing chars (i.e. ".x")
            # `index` should've pointed to the index +1 to the allowed char, but points to the allowed char itself
            index += 1
        return next_word, index

    def _get_next_words(self, text, start_idx, num_of_next_words=1):
        """
        Return a list of pairs of next words and next words included with separators,
        combined with their end indices.
        For example: Word `hand_job` has next words pairs: `job`, `_job`.
        """

        # Find the starting index of the next word
        start_idx_of_next_word = self._get_start_index_of_next_word(text, start_idx)

        # Return an empty string if there are no other words
        if start_idx_of_next_word >= len(text):
            return [("", start_idx_of_next_word), ("", start_idx_of_next_word)]

        # Combine the  words into a list
        next_word, end_index = self._get_next_word_and_end_index(
            text, start_idx_of_next_word
        )

        words = [
            (next_word, end_index),
            ("%s%s" % (text[start_idx:start_idx_of_next_word], next_word), end_index),
        ]
        if num_of_next_words > 1:
            words.extend(self._get_next_words(text, end_index, num_of_next_words - 1))

        return words

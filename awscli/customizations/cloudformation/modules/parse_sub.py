"""
This module parses CloudFormation Sub strings.

For example:

    !Sub abc-${AWS::Region}-def-${Foo}

The string is broken down into "words" that are one of four types:

    String: A literal string component
    Ref: A reference to another resource or paramter like ${Foo}
    AWS: An AWS pseudo-parameter like ${AWS::Region}
    GetAtt: A reference to an attribute like ${Foo.Bar}
"""

# pylint: disable=too-few-public-methods

from enum import Enum

DATA = " "  # Any other character
DOLLAR = "$"
OPEN = "{"
CLOSE = "}"
BANG = "!"
SPACE = " "


class WordType(Enum):
    "Word type enumeration"

    STR = 0  # A literal string fragment
    REF = 1  # ${ParamOrResourceName}
    AWS = 2  # ${AWS::X}
    GETATT = 3  # ${X.Y}
    CONSTANT = 4  # ${Const::name}


class State(Enum):
    "State machine enumeration"

    READSTR = 0
    READVAR = 1
    MAYBE = 2
    READLIT = 3


class SubWord:
    "A single word with a type and the word itself"

    def __init__(self, word_type, word):
        self.t = word_type
        self.w = word  # Does not include the ${} if it's not a STR

    def __str__(self):
        return f"{self.t} {self.w}"


def is_sub_needed(s):
    "Returns true if the string has any Sub variables"
    words = parse_sub(s)
    for w in words:
        if w.t != WordType.STR:
            return True
    return False


# pylint: disable=too-many-branches,too-many-statements
def parse_sub(sub_str, leave_bang=False):
    """
    Parse a Sub string

    :param leave_bang If this is True, leave the ! in literals
    :return list of words
    """
    words = []
    state = State.READSTR
    buf = ""
    last = ""
    for i, char in enumerate(sub_str):
        if char == DOLLAR:
            if state != State.READVAR:
                state = State.MAYBE
            else:
                # This is a literal $ inside a variable: "${AB$C}"
                buf += char
        elif char == OPEN:
            if state == State.MAYBE:
                # Peek to see if we're about to start a LITERAL !
                if len(sub_str) > i + 1 and sub_str[i + 1] == BANG:
                    # Treat this as part of the string, not a var
                    buf += "${"
                    state = State.READLIT
                else:
                    state = State.READVAR
                    # We're about to start reading a variable.
                    # Append the last word in the buffer if it's not empty
                    if buf:
                        words.append(SubWord(WordType.STR, buf))
                        buf = ""
            else:
                buf += char
        elif char == CLOSE:
            if state == State.READVAR:
                # Figure out what type it is
                if buf.startswith("AWS::"):
                    word_type = WordType.AWS
                elif buf.startswith("Const::"):
                    word_type = WordType.CONSTANT
                elif "." in buf:
                    word_type = WordType.GETATT
                else:
                    word_type = WordType.REF
                buf = buf.replace("AWS::", "", 1)
                buf = buf.replace("Const::", "", 1)
                # Very common typo to put Constants instead of Constant
                buf = buf.replace("Constants::", "", 1)
                words.append(SubWord(word_type, buf))
                buf = ""
                state = State.READSTR
            else:
                buf += char
        elif char == BANG:
            # ${!LITERAL} becomes ${LITERAL}
            if state == State.READLIT:
                # Don't write the ! to the string
                state = State.READSTR
                if leave_bang:
                    # Unless we actually want it
                    buf += char
            else:
                # This is a ! somewhere not related to a LITERAL
                buf += char
        elif char == SPACE:
            # Ignore spaces around Refs. ${ ABC } == ${ABC}
            if state != State.READVAR:
                buf += char
        else:
            if state == State.MAYBE:
                buf += last  # Put the $ back on the buffer
                state = State.READSTR
            buf += char

        last = char

    if buf:
        words.append(SubWord(WordType.STR, buf))

    # Handle malformed strings, like "ABC${XYZ"
    if state != State.READSTR:
        # Ended the string in the middle of a variable?
        raise ValueError("invalid string, unclosed variable")

    return words

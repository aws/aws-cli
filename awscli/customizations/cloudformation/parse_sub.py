import re

DATA = ' '  # Any other character
DOLLAR = '$'
OPEN = '{'
CLOSE = '}'
BANG = '!'

class WordType:
    STR = 0    # A literal string fragment
    REF = 1    # ${ParamOrResourceName}
    AWS = 2    # ${AWS::X}
    GETATT = 3 # ${X.Y}

class State:
    READSTR = 0
    READVAR = 1
    MAYBE = 2
    READLIT = 3



class SubWord:
    def __init__(self, word_type, word):
        self.T = word_type
        self.W = word  # Does not include the ${} if it's not a STR

def parse_sub(sub_str, leave_bang=False):
    words = []
    state = State.READSTR
    buf = ''
    i = -1
    last = ''
    for char in sub_str:
        i += 1
        if char == DOLLAR:
            if state != State.READVAR:
                state = State.MAYBE
            else:
                # This is a literal $ inside a variable: "${AB$C}"
                # TODO: Should that be an error? Is it valid?
                buf += char
        elif char == OPEN:
            if state == State.MAYBE:
                # Peek to see if we're about to start a LITERAL !
                if len(sub_str) > i+1 and sub_str[i+1] == BANG:
                    # Treat this as part of the string, not a var
                    buf += "${"
                    state = State.READLIT
                else:
                    state = State.READVAR
                    # We're about to start reading a variable.
                    # Append the last word in the buffer if it's not empty
                    if buf:
                        words.append(SubWord(WordType.STR, buf))
                        buf = ''
            else:
                buf += char
        elif char == CLOSE:
            if state == State.READVAR:
                # Figure out what type it is
                if buf.startswith("AWS::"):
                    word_type = WordType.AWS
                elif '.' in buf:
                    word_type = WordType.GETATT
                else:
                    word_type = WordType.REF
                buf = buf.replace("AWS::", "", 1)
                words.append(SubWord(word_type, buf))
                buf = ''
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


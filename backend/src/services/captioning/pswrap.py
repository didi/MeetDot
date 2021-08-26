from collections import Counter
from string import punctuation
import sys
import textwrap
import unicodedata

from zhon import hanzi


# Reference:
# https://github.com/python/cpython/blob/03648a2a91f9f1091cd21bd4cd6ca092ddb25640/Lib/textwrap.py
def pswrap(text, width=70, **kwargs):
    w = PunctuationSensitiveWrapper(width=width, **kwargs)
    return w.wrap(text)


# Reference:
# https://github.com/fgallaire/cjkwrap/blob/1bfe0516f58bace3f9f2f462892b7b3475702474/cjkwrap.py
def is_wide(char):
    """is_wide(unicode_char) -> boolean
    Return True if unicode_char is Fullwidth or Wide, False otherwise.
    Fullwidth and Wide CJK chars are double-width.
    """
    return unicodedata.east_asian_width(char) in ("F", "W")


# Reference:
# https://github.com/fgallaire/cjkwrap/blob/1bfe0516f58bace3f9f2f462892b7b3475702474/cjkwrap.py
def cjklen(text):
    """cjklen(object) -> integer

    Return the real width of an unicode text, the len of any other type.
    """
    return sum(2 if is_wide(char) else 1 for char in text)


# Reference:
# https://github.com/fgallaire/cjkwrap/blob/1bfe0516f58bace3f9f2f462892b7b3475702474/cjkwrap.py
def cjkslices(text, index):
    """cjkslices(object, integer) -> object, object

    Return the two slices of a text cut to the index.
    """
    ps_len = get_ps_len(text)
    if ps_len <= index:
        return text, u""
    i = 1
    # <= and i-1 to catch the last double length char of odd line
    while get_ps_len(text[:i]) <= index:
        i = i + 1
    return text[: i - 1], text[i - 1 :]


def get_ps_len(text):
    """get_ps_len(str) -> int

    Return the length of text excluding punctuations
    """
    counts = Counter(text)
    full_puncs = punctuation + hanzi.punctuation
    punctuation_len = sum(
        [
            counts.get(p, 0) if p in punctuation else 2 * counts.get(p, 0)
            for p in full_puncs
        ]
    )
    ps_len = cjklen(text) - punctuation_len
    return ps_len


# A text wrapper that can handle both latin and cjk chars
# len() changed to cjklen() where needed
# Reference:
# https://github.com/python/cpython/blob/03648a2a91f9f1091cd21bd4cd6ca092ddb25640/Lib/textwrap.py/
# https://github.com/fgallaire/cjkwrap/blob/1bfe0516f58bace3f9f2f462892b7b3475702474/cjkwrap.py
class PunctuationSensitiveWrapper(textwrap.TextWrapper):
    def _handle_long_word(self, reversed_chunks, cur_line, cur_len, width):
        """_handle_long_word(chunks : [string],
                             cur_line : [string],
                             cur_len : int, width : int)
        Handle a chunk of text (most likely a word, not whitespace) that
        is too long to fit in any line.
        """
        # Figure out when indent is larger than the specified width, and make
        # sure at least one character is stripped off on every pass
        if width < 1:
            space_left = 1
        else:
            space_left = width - cur_len

        # If we're allowed to break long words, then do so: put as much
        # of the next chunk onto the current line as will fit.
        if self.break_long_words:
            end = space_left
            chunk = reversed_chunks[-1]
            if self.break_on_hyphens and cjklen(chunk) > space_left:
                # break after last hyphen, but only if there are
                # non-hyphens before it
                hyphen = chunk.rfind("-", 0, space_left)
                if hyphen > 0 and any(c != "-" for c in chunk[:hyphen]):
                    end = hyphen + 1
            chunk_start, chunk_end = cjkslices(chunk, end)
            cur_line.append(chunk_start)
            reversed_chunks[-1] = chunk_end

        # Otherwise, we have to preserve the long word intact.  Only add
        # it to the current line if there's nothing already there --
        # that minimizes how much we violate the width constraint.
        elif not cur_line:
            cur_line.append(reversed_chunks.pop())

        # If we're not allowed to break long words, and there's already
        # text on the current line, do nothing.  Next time through the
        # main loop of _wrap_chunks(), we'll wind up here again, but
        # cur_len will be zero, so the next line will be entirely
        # devoted to the long word that we can't handle right now.

    def _wrap_chunks(self, chunks):
        """_wrap_chunks(chunks : [string]) -> [string]
        Wrap a sequence of text chunks and return a list of lines of
        length 'self.width' or less.  (If 'break_long_words' is false,
        some lines may be longer than this.)  Chunks correspond roughly
        to words and the whitespace between them: each chunk is
        indivisible (modulo 'break_long_words'), but a line break can
        come between any two chunks.  Chunks should not have internal
        whitespace; ie. a chunk is either all whitespace or a "word".
        Whitespace chunks will be removed from the beginning and end of
        lines, but apart from that whitespace is preserved.
        """
        lines = []
        if self.width <= 0:
            raise ValueError("invalid width %r (must be > 0)" % self.width)
        # raise error if CJK chars cannot be displayed
        if self.width == 1 and (
            sum(cjklen(chunk) for chunk in chunks) > sum(len(chunk) for chunk in chunks)
        ):
            raise ValueError("invalid width 1 (must be > 1 when CJK chars)")
        if self.max_lines is not None:
            if self.max_lines > 1:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent
            if cjklen(indent) + cjklen(self.placeholder.lstrip()) > self.width:
                raise ValueError("placeholder too large for max width")

        # Arrange in reverse order so items can be efficiently popped
        # from a stack of chucks.
        chunks.reverse()

        while chunks:

            # Start the list of chunks that will make up the current line.
            # cur_len is just the length of all the chunks in cur_line.
            cur_line = []
            cur_len = 0

            # Figure out which static string will prefix this line.
            if lines:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent

            # Maximum width for this line.
            width = self.width - cjklen(indent)

            # First chunk on line is whitespace -- drop it, unless this
            # is the very beginning of the text (ie. no lines started yet).
            if self.drop_whitespace and chunks[-1].strip() == "" and lines:
                del chunks[-1]

            while chunks:
                # CHANGE: ignore punctuations when getting length of chunk
                ps_len = get_ps_len(chunks[-1])
                # Can at least squeeze this chunk onto the current line.
                if cur_len + ps_len <= width:
                    cur_line.append(chunks.pop())
                    cur_len += ps_len

                # Nope, this line is full.
                else:
                    break

            # The current line is full, and the next chunk is too big to
            # fit on *any* line (not just this one).
            if chunks and cjklen(chunks[-1]) > width:
                self._handle_long_word(chunks, cur_line, cur_len, width)
                cur_len = sum(map(cjklen, cur_line))

            # If the last chunk on this line is all whitespace, drop it.
            if self.drop_whitespace and cur_line and cur_line[-1].strip() == "":
                cur_len -= cjklen(cur_line[-1])
                del cur_line[-1]

            if cur_line:
                if (
                    self.max_lines is None
                    or len(lines) + 1 < self.max_lines
                    or (
                        not chunks
                        or self.drop_whitespace
                        and len(chunks) == 1
                        and not chunks[0].strip()
                    )
                    and cur_len <= width
                ):
                    # Convert current line back to a string and store it in
                    # list of all lines (return value).
                    lines.append(indent + "".join(cur_line))
                else:
                    while cur_line:
                        if (
                            cur_line[-1].strip()
                            and cur_len + cjklen(self.placeholder) <= width
                        ):
                            cur_line.append(self.placeholder)
                            lines.append(indent + "".join(cur_line))
                            break
                        cur_len -= cjklen(cur_line[-1])
                        del cur_line[-1]
                    else:
                        if lines:
                            prev_line = lines[-1].rstrip()
                            if (
                                cjklen(prev_line) + cjklen(self.placeholder)
                                <= self.width
                            ):
                                lines[-1] = prev_line + self.placeholder
                                break
                        lines.append(indent + self.placeholder.lstrip())
                    break

        return lines

"""A differ for creating an HTML representations of proposal diffs."""

from __future__ import annotations

import html
import re
from difflib import Differ


class CombinedHtmlDiff:
    """Create an HTML representation of the differences between two pieces
    of text.
    """
    highlight_regex = re.compile(r'([\+\-\^]+)')

    def __init__(self, source, proposal):
        proposal = html.escape(proposal)

        differ = Differ()
        self.diff: list[str] = list(differ.compare(
            source.splitlines(keepends=True),
            proposal.splitlines(keepends=True),
        ))

    def make_text(self) -> str:
        return '\n'.join(self.diff)

    def make_html(self) -> str:
        """Return the HTML representation of the differences between
        `source` and `proposal`.

        :param source: the original text
        :param proposal: the proposed text
        """
        html = []
        diff = self.diff[:]
        line = diff.pop(0)
        next = diff.pop(0)
        while True:
            html.append(self._handle_line(line, next))
            line = next
            try:
                next = diff.pop(0)
            except IndexError:
                html.append(self._handle_line(line))
                break
        return ''.join(html).rstrip()

    def _handle_line(self, line: str, next: str | None = None) -> str:
        """Handle an individual line in a diff."""
        prefix = line[0]
        text = line[2:]

        if prefix == ' ':
            return text
        elif prefix == '?':
            return ''

        if next is not None and next[0] == '?':
            tag = prefix == '+' and 'ins' or 'del'
            text = self._highlight_text(text, next, tag)
        css_class = prefix == '+' and 'prop-added' or 'prop-removed'

        return f'<span class="{css_class}">{text.rstrip()}</span>\n'

    def _highlight_text(self, text: str, next: str, tag: str) -> str:
        """Highlight the specific changes made to a line by adding
        <ins> and <del> tags.
        """
        next = next[2:]
        new_text: list[str] = []
        start = 0
        for match in self.highlight_regex.finditer(next):
            new_text.extend((
                text[start:match.start()],
                f'<{tag}>',
                text[match.start():match.end()],
                f'</{tag}>',
            ))
            start = match.end()
        new_text.append(text[start:])
        return ''.join(new_text)

"""The default search adapter, does nothing."""

from __future__ import annotations

from sphinxcontrib.websupport.errors import NullSearchException
from sphinxcontrib.websupport.search import BaseSearch


class NullSearch(BaseSearch):
    """A search adapter that does nothing. Used when no search adapter
    is specified.
    """
    def feed(self, pagename, filename, title, doctree):
        pass

    def query(self, q):
        msg = 'No search adapter specified.'
        raise NullSearchException(msg)

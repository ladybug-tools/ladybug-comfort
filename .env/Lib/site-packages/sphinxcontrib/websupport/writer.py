"""websupport writer that adds comment-related annotations."""

from __future__ import annotations

from sphinx.writers.html import HTMLTranslator

from sphinxcontrib.websupport.utils import is_commentable


class WebSupportTranslator(HTMLTranslator):
    """
    Our custom HTML translator.
    """

    def __init__(self, builder, *args, **kwargs):
        HTMLTranslator.__init__(self, builder, *args, **kwargs)
        self.comment_class = 'sphinx-has-comment'

    def dispatch_visit(self, node):
        if is_commentable(node) and hasattr(node, 'uid'):
            self.handle_visit_commentable(node)
        HTMLTranslator.dispatch_visit(self, node)

    def handle_visit_commentable(self, node):
        # We will place the node in the HTML id attribute. If the node
        # already has an id (for indexing purposes) put an empty
        # span with the existing id directly before this node's HTML.
        self.add_db_node(node)
        if node.attributes['ids']:
            self.body.append(f'<span id="{node.attributes["ids"][0]}"></span>')
        node.attributes['ids'] = [f's{node.uid}']
        node.attributes['classes'].append(self.comment_class)

    def add_db_node(self, node):
        storage = self.builder.storage  # type: ignore[attr-defined]
        if not storage.has_node(node.uid):
            storage.add_node(id=node.uid,
                             document=self.builder.current_docname,
                             source=node.rawsource or node.astext())

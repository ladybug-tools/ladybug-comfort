"""Builder for the web support extension."""

from __future__ import annotations

import html
import os
import posixpath
import shutil
from os import path
from typing import TYPE_CHECKING, Any

from docutils.io import StringOutput
from sphinx.jinja2glue import BuiltinTemplateLoader
from sphinx.util.osutil import copyfile, ensuredir, os_path, relative_uri

from sphinxcontrib.serializinghtml import PickleHTMLBuilder
from sphinxcontrib.websupport import package_dir
from sphinxcontrib.websupport.utils import is_commentable
from sphinxcontrib.websupport.writer import WebSupportTranslator

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from docutils import nodes
    from sphinx.application import Sphinx
    from sphinx.builders.html._assets import _CascadingStyleSheet, _JavaScript

    from sphinxcontrib.websupport.search import BaseSearch

RESOURCES = [
    'ajax-loader.gif',
    'comment-bright.png',
    'comment-close.png',
    'comment.png',
    'down-pressed.png',
    'down.png',
    'up-pressed.png',
    'up.png',
    'websupport.js',
]


class WebSupportBuilder(PickleHTMLBuilder):
    """
    Builds documents for the web support package.
    """
    name = 'websupport'
    default_translator_class = WebSupportTranslator
    versioning_compare = True  # for commentable node's uuid stability.

    def init(self) -> None:
        super().init()
        # templates are needed for this builder, but the serializing
        # builder does not initialize them
        self.init_templates()
        if not isinstance(self.templates, BuiltinTemplateLoader):
            msg = 'websupport builder must be used with the builtin templates'
            raise RuntimeError(msg)
        # add our custom JS
        self.add_js_file('websupport.js')

    @property
    def versioning_method(self) -> Callable[[nodes.Node], bool]:  # type: ignore[override]
        return is_commentable

    def set_webinfo(
        self,
        staticdir: str,
        virtual_staticdir: str,
        search: BaseSearch,
        storage: str,
    ) -> None:
        self.staticdir = staticdir
        self.virtual_staticdir = virtual_staticdir
        self.search: BaseSearch = search  # type: ignore[assignment]
        self.storage = storage

    def prepare_writing(self, docnames: Iterable[str]) -> None:
        super().prepare_writing(set(docnames))
        self.globalcontext['no_search_suffix'] = True

    def write_doc(self, docname: str, doctree: nodes.document) -> None:
        destination = StringOutput(encoding='utf-8')
        doctree.settings = self.docsettings

        self.secnumbers = self.env.toc_secnumbers.get(docname, {})
        self.fignumbers = self.env.toc_fignumbers.get(docname, {})
        self.imgpath = '/' + posixpath.join(self.virtual_staticdir, self.imagedir)
        self.dlpath = '/' + posixpath.join(self.virtual_staticdir, '_downloads')
        self.current_docname = docname
        self.docwriter.write(doctree, destination)
        self.docwriter.assemble_parts()
        body = self.docwriter.parts['fragment']
        metatags = self.docwriter.clean_meta

        ctx = self.get_doc_context(docname, body, metatags)
        self.handle_page(docname, ctx, event_arg=doctree)

    def write_doc_serialized(self, docname: str, doctree: nodes.document) -> None:
        self.imgpath = '/' + posixpath.join(self.virtual_staticdir, self.imagedir)
        self.post_process_images(doctree)
        title_node = self.env.longtitles.get(docname)
        title = title_node and self.render_partial(title_node)['title'] or ''
        self.index_page(docname, doctree, title)

    def load_indexer(self, docnames: Iterable[str]) -> None:
        self.indexer = self.search  # type: ignore[assignment]
        self.indexer.init_indexing(changed=list(docnames))  # type: ignore[union-attr]

    def _render_page(
        self,
        pagename: str,
        addctx: dict,
        templatename: str,
        event_arg: Any = None,
    ) -> tuple[dict, dict]:
        # This is mostly copied from StandaloneHTMLBuilder. However, instead
        # of rendering the template and saving the html, create a context
        # dict and pickle it.
        ctx = self.globalcontext.copy()
        ctx['pagename'] = pagename

        def pathto(otheruri: str, resource: bool = False,
                   baseuri: str = self.get_target_uri(pagename)) -> str:
            if resource and '://' in otheruri:
                return otheruri
            elif not resource:
                otheruri = self.get_target_uri(otheruri)
                return relative_uri(baseuri, otheruri) or '#'
            else:
                return '/' + posixpath.join(self.virtual_staticdir, otheruri)
        ctx['pathto'] = pathto
        ctx['hasdoc'] = lambda name: name in self.env.all_docs
        ctx['encoding'] = self.config.html_output_encoding
        ctx['toctree'] = lambda **kw: self._get_local_toctree(pagename, **kw)
        self.add_sidebars(pagename, ctx)
        ctx.update(addctx)

        def css_tag(css: _CascadingStyleSheet) -> str:
            attrs = []
            for key, value in css.attributes.items():
                if value is not None:
                    attrs.append(f'{key}="{html.escape(value, quote=True)}"')
            uri = pathto(os.fspath(css.filename), resource=True)
            return f'<link {" ".join(sorted(attrs))} href="{uri}" />'

        ctx['css_tag'] = css_tag

        def js_tag(js: _JavaScript) -> str:
            if not hasattr(js, 'filename'):
                # str value (old styled)
                return f'<script src="{pathto(js, resource=True)}"></script>'  # type: ignore[arg-type]

            attrs = []
            body = js.attributes.get('body', '')
            for key, value in js.attributes.items():
                if key == 'body':
                    continue
                if value is not None:
                    attrs.append(f'{key}="{html.escape(value, quote=True)}"')

            if not js.filename:
                if attrs:
                    return f'<script {" ".join(sorted(attrs))}>{body}</script>'
                return f'<script>{body}</script>'

            uri = pathto(os.fspath(js.filename), resource=True)
            if attrs:
                return f'<script {" ".join(sorted(attrs))} src="{uri}"></script>'
            return f'<script src="{uri}"></script>'

        ctx['js_tag'] = js_tag

        newtmpl = self.app.emit_firstresult('html-page-context', pagename,
                                            templatename, ctx, event_arg)
        if newtmpl:
            templatename = newtmpl

        # create a dict that will be pickled and used by webapps
        doc_ctx = {
            'body': ctx.get('body', ''),
            'title': ctx.get('title', ''),
            'css': ctx.get('css', ''),
            'script': ctx.get('script', ''),
        }
        # partially render the html template to get at interesting macros
        template = self.templates.environment.get_template(templatename)
        template_module = template.make_module(ctx)
        for item in ['sidebar', 'relbar', 'script', 'css']:
            if hasattr(template_module, item):
                doc_ctx[item] = getattr(template_module, item)()

        return ctx, doc_ctx

    def handle_page(self, pagename: str, addctx: dict, templatename: str = 'page.html',
                    outfilename: str | None = None, event_arg: Any = None) -> None:
        ctx, doc_ctx = self._render_page(pagename, addctx,
                                         templatename, event_arg)

        if not outfilename:
            outfilename = path.join(self.outdir, 'pickles',
                                    os_path(pagename) + self.out_suffix)
        ensuredir(path.dirname(outfilename))
        self.dump_context(doc_ctx, outfilename)

        # if there is a source file, copy the source file for the
        # "show source" link
        if ctx.get('sourcename'):
            source_name = path.join(self.staticdir,
                                    '_sources', os_path(ctx['sourcename']))
            ensuredir(path.dirname(source_name))
            copyfile(self.env.doc2path(pagename), source_name)

    def handle_finish(self) -> None:
        # get global values for css and script files
        _, doc_ctx = self._render_page('tmp', {}, 'page.html')
        self.globalcontext['css'] = doc_ctx['css']
        self.globalcontext['script'] = doc_ctx['script']

        super().handle_finish()

        # move static stuff over to separate directory
        directories = [self.imagedir, '_static']
        for directory in directories:
            src = path.join(self.outdir, directory)
            dst = path.join(self.staticdir, directory)
            if path.isdir(src):
                if path.isdir(dst):
                    shutil.rmtree(dst)
                shutil.move(src, dst)
        self.copy_resources()

    def copy_resources(self) -> None:
        # copy resource files to static dir
        dst = path.join(self.staticdir, '_static')

        if path.isdir(dst):
            for resource in RESOURCES:
                src = path.join(package_dir, 'files', resource)
                shutil.copy(src, dst)

    def dump_search_index(self) -> None:
        self.indexer.finish_indexing()  # type: ignore[union-attr]


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_builder(WebSupportBuilder)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }

"""Sphinx extension that writes a Markdown copy of each page next to its HTML.

Uses the Markdown translator from sphinx-markdown-builder, but runs it from
the HTML builder's ``write_doc`` instead of as a separate
``sphinx-build -b markdown``: conf.py regenerates every source file, so a
second build would re-read all ~20k documents. Converting the doctree the
HTML builder just rendered also avoids resolving it a second time, and runs
in the worker processes when writing in parallel.

Internal links point at the sibling ``.md`` files.
"""

import json
import posixpath
import re
from urllib.parse import unquote, urlsplit, urlunsplit

from docutils import nodes
from sphinx_markdown_builder import MarkdownBuilder
from sphinx_markdown_builder.escape import escape_markdown_chars


def _skip_node(self, node):
    raise nodes.SkipNode


def _visit_literal(self, node):
    # Use a longer delimiter so backticks inside code samples remain literal.
    # DataBrew's ":col1": "`Column A`". becomes ``":col1": "`Column A`".``.
    text = node.astext()
    longest_run = max((len(run) for run in re.findall(r'`+', text)), default=0)
    delimiter = '`' * (longest_run + 1)
    # Padding separates edge backticks from the delimiter, and preserves
    # surrounding spaces that Markdown would otherwise strip.
    if (
        text.startswith('`')
        or text.endswith('`')
        or (text.startswith(' ') and text.endswith(' ') and text.strip())
    ):
        text = f' {text} '
    self.add(f'{delimiter}{text}{delimiter}')
    raise nodes.SkipNode


def _visit_problematic(self, node):
    # Markup that docutils could not parse. The translator puts it in its own
    # code block, which splits the surrounding paragraph or list item, so
    # write it inline like the HTML does.
    self.add(escape_markdown_chars(node.astext()))
    raise nodes.SkipNode


def _visit_attribution(self, node):
    # docutils parses a block quote line starting with "--" as an attribution,
    # which the translator does not handle and drops. In the CLI reference
    # these are option examples, e.g. ``--document-version "3"`` in
    # ``aws ssm send-command``, so restore the "--" that docutils consumed.
    self.add(f'--{escape_markdown_chars(node.astext())}', prefix_eol=1)
    raise nodes.SkipNode


def _create_markdown_builder(app):
    # Builder.__init__ adds the builder's name and format to app.tags, which
    # would make ``.. only:: markdown`` content show up in the HTML output.
    tags = set(app.tags)
    builder = MarkdownBuilder(app, app.env)
    for tag in set(app.tags) - tags:
        app.tags.remove(tag)
    builder.init()
    builder.prepare_writing(set())
    return builder


def _link_to_markdown(doctree, docname, found_docs):
    # Rewrite links to generated HTML documents to their Markdown counterparts.
    for node in doctree.findall(nodes.reference):
        try:
            uri = urlsplit(node.get('refuri', ''))
        except ValueError:
            continue
        if (
            uri.scheme
            or uri.netloc
            or uri.path.startswith('/')
            or not uri.path.endswith('.html')
        ):
            continue
        # Explicit relative links lack Sphinx's "internal" flag. Only
        # rewrite them when their target is a generated document.
        target = posixpath.normpath(
            posixpath.join(posixpath.dirname(docname), unquote(uri.path))
        )[:-5]
        if node.get('internal') or target in found_docs:
            node['refuri'] = urlunsplit(uri._replace(path=uri.path[:-5] + '.md'))


def _remove_breadcrumbs(doctree):
    # Generated pages start with a "[ aws . s3api ]" breadcrumb paragraph
    # (see doc_breadcrumbs in awscli/clidocs.py), which is navigation noise
    # in Markdown. It is the first paragraph, before the title section.
    for node in doctree.children:
        if isinstance(node, nodes.section):
            return
        if isinstance(node, nodes.paragraph):
            text = node.astext()
            if text.startswith('[ aws') and text.endswith(' ]'):
                doctree.remove(node)
            return


def _guess_code_language(code):
    code = code.lstrip()
    if code.startswith('aws '):
        return 'bash'
    # "JSON Syntax" templates and some example outputs are not valid JSON,
    # e.g. "true|false", "..." or trailing commas. Lists must open with a
    # value so INI sections such as "[default]" are not treated as JSON.
    if code.startswith('{') or re.match(r'\[\s*[\[{"]', code):
        return 'json'
    try:
        json.loads(code)
    except ValueError:
        return ''
    return 'json'


def _set_code_languages(doctree):
    # Code blocks without an explicit language get Sphinx's "default", which
    # is not a language Markdown renderers know, so guess one instead.
    for node in doctree.findall(nodes.literal_block):
        if node.get('language') == 'default':
            node['language'] = _guess_code_language(node.astext())


def _install(app):
    if app.builder.name != 'html':
        return
    markdown_builder = _create_markdown_builder(app)
    write_html = app.builder.write_doc

    def write_doc(docname, doctree):
        write_html(docname, doctree)
        # The doctree is discarded after this, so it can be modified in place
        _remove_breadcrumbs(doctree)
        _link_to_markdown(doctree, docname, app.env.found_docs)
        _set_code_languages(doctree)
        markdown_builder.write_doc(docname, doctree)

    app.builder.write_doc = write_doc


def _add_markdown_url(app, pagename, templatename, context, doctree):
    # Only pages built from a source document have a Markdown copy, not
    # generated pages such as genindex, search, or 404.
    if app.builder.name != 'html' or doctree is None:
        return
    # The Markdown file is written next to the HTML page, so the link is
    # relative to the page's own directory.
    context['markdown_url'] = (
        posixpath.basename(pagename) + app.config.markdown_file_suffix
    )


def setup(app):
    app.setup_extension('sphinx_markdown_builder')
    # The translator does not handle meta nodes and would warn for every
    # page. The description is already in the HTML, so drop it.
    app.add_node(nodes.meta, override=True, markdown=(_skip_node, None))
    app.add_node(nodes.literal, override=True, markdown=(_visit_literal, None))
    app.add_node(
        nodes.problematic, override=True, markdown=(_visit_problematic, None)
    )
    app.add_node(
        nodes.attribution, override=True, markdown=(_visit_attribution, None)
    )
    app.connect('builder-inited', _install)
    app.connect('html-page-context', _add_markdown_url)
    return {
        'version': '1.0',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }

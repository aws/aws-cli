"""Sphinx extension that makes parallel HTML writes scale for large doc sets.

When writing in parallel (``sphinx-build -j N``), Sphinx loads and resolves
every doctree, runs post-transforms, and feeds the search index in the main
process, and only renders HTML in the worker processes. With ~20k documents
the main process becomes the bottleneck and leaves the workers idle.

This extension moves loading, resolving, post-transforms and search indexing
into the worker processes. Each worker sends back the images it found and the
search index entries for its documents, which are merged into the main
process's builder before the search index and images are written out.

This is the approach proposed upstream in
https://github.com/sphinx-doc/sphinx/pull/11746, specialised for the HTML
builder. It overrides a private Sphinx method, so it must be re-validated
when upgrading Sphinx (see tests/unit/test_doc_extensions.py).
"""

import types

from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.build_phase import BuildPhase
from sphinx.util.display import status_iterator
from sphinx.util.parallel import ParallelTasks, make_chunks

logger = logging.getLogger(__name__)

# Per-document search index data populated by IndexBuilder.feed()
_INDEX_DOC_ATTRS = ('_titles', '_filenames', '_all_titles', '_index_entries')
# Per-word search index data populated by IndexBuilder.feed()
_INDEX_WORD_ATTRS = ('_mapping', '_title_mapping')


def _resolve_and_write(builder, docname):
    builder.app.phase = BuildPhase.RESOLVING
    doctree = builder.env.get_and_resolve_doctree(docname, builder)
    builder.app.phase = BuildPhase.WRITING
    builder.write_doc_serialized(docname, doctree)
    builder.write_doc(docname, doctree)


def _write_parallel(self, docnames, nproc):
    def write_process(docs):
        # Runs in a forked worker: start with empty collections so that only
        # the data for this chunk's documents is sent back.
        self.images = {}
        if self.indexer is not None:
            for attr in _INDEX_DOC_ATTRS + _INDEX_WORD_ATTRS:
                setattr(self.indexer, attr, {})
        for docname in docs:
            _resolve_and_write(self, docname)
        index = None
        if self.indexer is not None:
            index = {
                attr: getattr(self.indexer, attr)
                for attr in _INDEX_DOC_ATTRS + _INDEX_WORD_ATTRS
            }
        return self.images, index

    # Chunks are contiguous slices of the sorted docnames and can finish in
    # any order. Parts of the search index are dumped in insertion order, so
    # results are merged in chunk order to match a serial build exactly.
    pending = {}
    next_chunk = 0

    def merge_result(result):
        images, index = result
        self.images.update(images)
        if index is not None:
            for attr in _INDEX_DOC_ATTRS:
                getattr(self.indexer, attr).update(index[attr])
            for attr in _INDEX_WORD_ATTRS:
                mapping = getattr(self.indexer, attr)
                for word, word_docnames in index[attr].items():
                    mapping.setdefault(word, set()).update(word_docnames)

    def on_chunk_done(docs, result):
        nonlocal next_chunk
        pending[chunk_index[docs[0]]] = result
        while next_chunk in pending:
            merge_result(pending.pop(next_chunk))
            next_chunk += 1
        next(progress)

    # warm up caches/compile templates using the first document
    firstname, docnames = docnames[0], docnames[1:]
    _resolve_and_write(self, firstname)

    tasks = ParallelTasks(nproc)
    chunks = make_chunks(docnames, nproc)
    chunk_index = {chunk[0]: i for i, chunk in enumerate(chunks)}
    progress = status_iterator(
        chunks,
        __('writing output... '),
        'darkgreen',
        len(chunks),
        self.app.verbosity,
    )
    for chunk in chunks:
        tasks.add_task(write_process, chunk, on_chunk_done)
    tasks.join()
    logger.info('')


def _install(app):
    if isinstance(app.builder, StandaloneHTMLBuilder):
        app.builder._write_parallel = types.MethodType(
            _write_parallel, app.builder
        )


def setup(app):
    app.connect('builder-inited', _install)
    return {
        'version': '1.0',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }

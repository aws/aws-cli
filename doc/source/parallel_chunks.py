"""Sphinx extension that makes parallel reads scale for large doc sets.

When reading in parallel (``sphinx-build -j N``), Sphinx splits the documents
into many small chunks and forks a process per chunk. Each process pickles its
entire build environment (including the TOCs and titles of every document read
so far) and sends it back to the main process to be merged. With ~20k
documents, unpickling those environments in the main process becomes the
bottleneck and leaves the worker processes idle.

This extension uses one chunk per process while reading, so every process is
forked while the environment is still small and only sends back the documents
it read. Documents are interleaved across chunks so that expensive services,
which are adjacent alphabetically, are spread across all processes. The
chunking used for writing is unchanged.

It patches Sphinx internals, so it must be re-validated when
upgrading Sphinx (see tests/unit/test_doc_extensions.py).
"""

import sphinx.builders

_original_make_chunks = sphinx.builders.make_chunks
_reading = False


def _make_chunks(arguments, nproc, maxbatch=10):
    if not _reading:
        return _original_make_chunks(arguments, nproc, maxbatch)
    nchunks = max(1, min(nproc, len(arguments)))
    return [arguments[i::nchunks] for i in range(nchunks)]


def _start_reading(app, env, docnames):
    global _reading
    _reading = True


def _stop_reading(app, env):
    global _reading
    _reading = False
    # Parallel reads merge documents in the order chunks finish, while a
    # serial build reads them in sorted order. Some output (e.g. the search
    # index) follows this order, so restore the serial order.
    ordered = dict(sorted(env.all_docs.items()))
    env.all_docs.clear()
    env.all_docs.update(ordered)


def setup(app):
    sphinx.builders.make_chunks = _make_chunks
    app.connect('env-before-read-docs', _start_reading)
    app.connect('env-updated', _stop_reading)
    return {
        'version': '1.0',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }

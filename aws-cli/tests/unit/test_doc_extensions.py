# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
DOCS_LOCK_FILE = REPO_ROOT / 'requirements-docs-lock.txt'

# The Sphinx version that the parallel_chunks and parallel_write extensions
# and the parallel-safe guzzle theme (doc/source) were validated against.
VALIDATED_SPHINX_VERSION = '6.2.0'

REVALIDATE_INSTRUCTIONS = """\
Sphinx was upgraded from {validated} to {locked} in {lock_file}.

The parallel_chunks and parallel_write extensions in doc/source patch
Sphinx internals, so they can silently drop pages or content from the
docs, sitemap.xml or searchindex.js after a Sphinx upgrade. Before updating
VALIDATED_SPHINX_VERSION in {test_file}, build the docs serially and in
parallel with the new Sphinx version and confirm the output is identical:

    cd doc
    sphinx-build -b html -d /tmp/serial/doctrees source /tmp/serial/html
    sphinx-build -j auto -b html -d /tmp/parallel/doctrees source \\
        /tmp/parallel/html
    diff -r -x .buildinfo /tmp/serial/html /tmp/parallel/html

The diff must be empty (.buildinfo hashes the build config, so it differs),
and both builds must report the same number of warnings.
"""


def _get_locked_sphinx_version():
    match = re.search(
        r'^sphinx==(\S+)', DOCS_LOCK_FILE.read_text(), re.MULTILINE
    )
    assert match is not None, f'sphinx is not pinned in {DOCS_LOCK_FILE}'
    return match.group(1)


def test_sphinx_version_is_validated_for_parallel_doc_extensions():
    locked = _get_locked_sphinx_version()
    assert locked == VALIDATED_SPHINX_VERSION, REVALIDATE_INSTRUCTIONS.format(
        validated=VALIDATED_SPHINX_VERSION,
        locked=locked,
        lock_file=DOCS_LOCK_FILE.relative_to(REPO_ROOT),
        test_file=Path(__file__).relative_to(REPO_ROOT),
    )

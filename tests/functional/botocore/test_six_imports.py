import ast
import os

import pytest

import botocore

ROOTDIR = os.path.dirname(botocore.__file__)


def _all_files():
    for rootdir, dirnames, filenames in os.walk(ROOTDIR):
        if 'vendored' in dirnames:
            # We don't need to lint our vendored packages.
            dirnames.remove('vendored')
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            yield os.path.join(rootdir, filename)


@pytest.mark.parametrize("filename", _all_files())
def test_no_bare_six_imports(filename):
    with open(filename) as f:
        contents = f.read()
        parsed = ast.parse(contents, filename)
        SixImportChecker(filename).visit(parsed)


class SixImportChecker(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename

    def visit_Import(self, node):
        for alias in node.names:
            if getattr(alias, 'name', '') == 'six':
                line = self._get_line_content(self.filename, node.lineno)
                raise AssertionError(
                    f"A bare 'import six' was found in {self.filename}:\n"
                    f"\n{node.lineno}: {line}\n"
                    "Please use 'from botocore.compat import six' instead"
                )

    def visit_ImportFrom(self, node):
        if node.module == 'six':
            line = self._get_line_content(self.filename, node.lineno)
            raise AssertionError(
                f"A bare 'from six import ...' was found in {self.filename}:\n"
                f"\n{node.lineno}:{line}\n"
                "Please use 'from botocore.compat import six' instead"
            )

    def _get_line_content(self, filename, lineno):
        with open(filename) as f:
            contents = f.readlines()
            return contents[lineno - 1]

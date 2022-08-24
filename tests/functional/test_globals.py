import os
import unittest

from awscli.testutils import create_clidriver
from awscli.clidocs import (
    GLOBAL_OPTIONS_FILE, GLOBAL_OPTIONS_SYNOPSIS_FILE,
    GlobalOptionsDocumenter
)


class TestGlobalOptionsDocumenter(unittest.TestCase):
    def setUp(self):
        self.driver = create_clidriver()
        self.help_command = self.driver.create_help_command()
        self.globals = GlobalOptionsDocumenter(self.help_command)

    def test_doc_global_options_match_saved_content(self):
        with open(GLOBAL_OPTIONS_FILE, 'r') as f:
            self.assertEqual(self.globals.doc_global_options(), f.read())

    def test_doc_global_synopsis_match_saved_content(self):
        with open(GLOBAL_OPTIONS_SYNOPSIS_FILE, 'r') as f:
            self.assertEqual(self.globals.doc_global_synopsis(), f.read())

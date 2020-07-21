import os
import tempfile
import shutil
import codecs

from awscli.testutils import unittest
from awscli.utils import write_exception


class TestWriteException(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.outfile = os.path.join(self.tempdir, 'stdout')

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_write_exception(self):
        error_message = "Some error message."
        ex = Exception(error_message)
        with codecs.open(self.outfile, 'w+', encoding='utf-8') as outfile:
            write_exception(ex, outfile)
            outfile.seek(0)

            expected_output = (
                "\n%s\n" % error_message
            )
            self.assertEqual(outfile.read(), expected_output)


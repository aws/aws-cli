from tests import unittest
import os
import tempfile
import shutil
import ntpath

from six.moves import queue
import mock

from awscli.customizations.s3.utils import find_bucket_key, find_chunksize
from awscli.customizations.s3.utils import NoBlockQueue, ReadFileChunk
from awscli.customizations.s3.utils import relative_path
from awscli.customizations.s3.constants import MAX_SINGLE_UPLOAD_SIZE


class FindBucketKey(unittest.TestCase):
    """
    This test ensures the find_bucket_key function works when
    unicode is used.
    """
    def test_unicode(self):
        s3_path = '\u1234' + u'/' + '\u5678'
        bucket, key = find_bucket_key(s3_path)
        self.assertEqual(bucket, '\u1234')
        self.assertEqual(key, '\u5678')


class FindChunksizeTest(unittest.TestCase):
    """
    This test ensures that the ``find_chunksize`` function works
    as expected.
    """
    def test_small_chunk(self):
        """
        This test ensures if the ``chunksize`` is appropriate to begin with,
        it does not change.
        """
        chunksize = 7 * (1024 ** 2)
        size = 8 * (1024 ** 2)
        self.assertEqual(find_chunksize(size, chunksize), chunksize)

    def test_large_chunk(self):
        """
        This test ensures if the ``chunksize`` adapts to an appropriate
        size because the original ``chunksize`` is too small.
        """
        chunksize = 7 * (1024 ** 2)
        size = 8 * (1024 ** 3)
        self.assertEqual(find_chunksize(size, chunksize), chunksize * 2)

    def test_super_chunk(self):
        """
        This tests to ensure that the ``chunksize can never be larger than
        the ``MAX_SINGLE_UPLOAD_SIZE``
        """
        chunksize = MAX_SINGLE_UPLOAD_SIZE + 1
        size = MAX_SINGLE_UPLOAD_SIZE * 2
        self.assertEqual(find_chunksize(size, chunksize),
                         MAX_SINGLE_UPLOAD_SIZE)


class TestNoBlockQueue(unittest.TestCase):
    def test_max_size(self):
        q = NoBlockQueue(maxsize=3)
        q.put(1)
        q.put(2)
        q.put(3)
        with self.assertRaises(queue.Full):
            q.put(4, block=False)

    def test_no_max_size(self):
        q = NoBlockQueue()
        q.put(1)
        q.put(2)
        q.put(3)
        q.put(4)
        self.assertEqual(q.get(), 1)
        self.assertEqual(q.get(), 2)
        self.assertEqual(q.get(), 3)
        self.assertEqual(q.get(), 4)


class TestReadFileChunk(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_read_entire_chunk(self):
        filename = os.path.join(self.tempdir, 'foo')
        f = open(filename, 'wb')
        f.write(b'onetwothreefourfivesixseveneightnineten')
        f.flush()
        chunk = ReadFileChunk(filename, start_byte=0, size=3)
        self.assertEqual(chunk.read(), b'one')
        self.assertEqual(chunk.read(), b'')

    def test_read_with_amount_size(self):
        filename = os.path.join(self.tempdir, 'foo')
        f = open(filename, 'wb')
        f.write(b'onetwothreefourfivesixseveneightnineten')
        f.flush()
        chunk = ReadFileChunk(filename, start_byte=11, size=4)
        self.assertEqual(chunk.read(1), b'f')
        self.assertEqual(chunk.read(1), b'o')
        self.assertEqual(chunk.read(1), b'u')
        self.assertEqual(chunk.read(1), b'r')
        self.assertEqual(chunk.read(1), b'')

    def test_read_past_end_of_file(self):
        filename = os.path.join(self.tempdir, 'foo')
        f = open(filename, 'wb')
        f.write(b'onetwothreefourfivesixseveneightnineten')
        f.flush()
        chunk = ReadFileChunk(filename, start_byte=36, size=100000)
        self.assertEqual(chunk.read(), b'ten')
        self.assertEqual(chunk.read(), b'')
        self.assertEqual(len(chunk), 3)


class TestRelativePath(unittest.TestCase):
    def test_relpath_normal(self):
        self.assertEqual(relative_path('/tmp/foo/bar', '/tmp/foo'),
                         '.' + os.sep + 'bar')

    # We need to patch out relpath with the ntpath version so
    # we can simulate testing drives on windows.
    @mock.patch('os.path.relpath', ntpath.relpath)
    def test_relpath_with_error(self):
        # Just want to check we don't get an exception raised,
        # which is what was happening previously.
        self.assertIn(r'foo\bar', relative_path(r'c:\foo\bar'))


if __name__ == "__main__":
    unittest.main()

from tests import unittest
from six.moves import queue
import tempfile

from awscli.customizations.s3.utils import find_bucket_key, find_chunksize
from awscli.customizations.s3.utils import NoBlockQueue, ReadFileChunk
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
    def test_read_entire_chunk(self):
        f = tempfile.NamedTemporaryFile()
        f.write('onetwothreefourfivesixseveneightnineten')
        f.flush()
        chunk = ReadFileChunk(f.name, start_byte=0, size=3)
        self.assertEqual(chunk.read(), 'one')
        self.assertEqual(chunk.read(), '')

    def test_read_with_amount_size(self):
        f = tempfile.NamedTemporaryFile()
        f.write('onetwothreefourfivesixseveneightnineten')
        f.flush()
        chunk = ReadFileChunk(f.name, start_byte=11, size=4)
        self.assertEqual(chunk.read(1), 'f')
        self.assertEqual(chunk.read(1), 'o')
        self.assertEqual(chunk.read(1), 'u')
        self.assertEqual(chunk.read(1), 'r')
        self.assertEqual(chunk.read(1), '')

    def test_read_past_end_of_file(self):
        f = tempfile.NamedTemporaryFile()
        f.write('onetwothreefourfivesixseveneightnineten')
        f.flush()
        chunk = ReadFileChunk(f.name, start_byte=36, size=100000)
        self.assertEqual(chunk.read(), 'ten')
        self.assertEqual(chunk.read(), '')
        self.assertEqual(len(chunk), 3)


if __name__ == "__main__":
    unittest.main()

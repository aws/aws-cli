from awscli.testutils import unittest, temporary_file
import argparse
import os
import tempfile
import shutil
import ntpath
import time
import datetime

import mock
from dateutil.tz import tzlocal
from nose.tools import assert_equal

from botocore.hooks import HierarchicalEmitter
from awscli.customizations.s3.utils import find_bucket_key, find_chunksize
from awscli.customizations.s3.utils import ReadFileChunk
from awscli.customizations.s3.utils import relative_path
from awscli.customizations.s3.utils import StablePriorityQueue
from awscli.customizations.s3.utils import BucketLister
from awscli.customizations.s3.utils import ScopedEventHandler
from awscli.customizations.s3.utils import get_file_stat
from awscli.customizations.s3.utils import AppendFilter
from awscli.customizations.s3.utils import create_warning
from awscli.customizations.s3.utils import human_readable_size
from awscli.customizations.s3.utils import human_readable_to_bytes
from awscli.customizations.s3.utils import MAX_SINGLE_UPLOAD_SIZE


def test_human_readable_size():
    yield _test_human_size_matches, 1, '1 Byte'
    yield _test_human_size_matches, 10, '10 Bytes'
    yield _test_human_size_matches, 1000, '1000 Bytes'
    yield _test_human_size_matches, 1024, '1.0 KiB'
    yield _test_human_size_matches, 1024 ** 2, '1.0 MiB'
    yield _test_human_size_matches, 1024 ** 2, '1.0 MiB'
    yield _test_human_size_matches, 1024 ** 3, '1.0 GiB'
    yield _test_human_size_matches, 1024 ** 4, '1.0 TiB'
    yield _test_human_size_matches, 1024 ** 5, '1.0 PiB'
    yield _test_human_size_matches, 1024 ** 6, '1.0 EiB'

    # Round to the nearest block.
    yield _test_human_size_matches, 1024 ** 2 - 1, '1.0 MiB'
    yield _test_human_size_matches, 1024 ** 3 - 1, '1.0 GiB'


def _test_human_size_matches(bytes_int, expected):
    assert_equal(human_readable_size(bytes_int), expected)


def test_convert_human_readable_to_bytes():
    yield _test_convert_human_readable_to_bytes, "1", 1
    yield _test_convert_human_readable_to_bytes, "1024", 1024
    yield _test_convert_human_readable_to_bytes, "1KB", 1024
    yield _test_convert_human_readable_to_bytes, "1kb", 1024
    yield _test_convert_human_readable_to_bytes, "1MB", 1024 ** 2
    yield _test_convert_human_readable_to_bytes, "1GB", 1024 ** 3
    yield _test_convert_human_readable_to_bytes, "1TB", 1024 ** 4

    # Also because of the "ls" output for s3, we support
    # the IEC "mebibyte" format (MiB).
    yield _test_convert_human_readable_to_bytes, "1KiB", 1024
    yield _test_convert_human_readable_to_bytes, "1kib", 1024
    yield _test_convert_human_readable_to_bytes, "1MiB", 1024 ** 2
    yield _test_convert_human_readable_to_bytes, "1GiB", 1024 ** 3
    yield _test_convert_human_readable_to_bytes, "1TiB", 1024 ** 4


def _test_convert_human_readable_to_bytes(size_str, expected):
    assert_equal(human_readable_to_bytes(size_str), expected)


class AppendFilterTest(unittest.TestCase):
    def test_call(self):
        parser = argparse.ArgumentParser()

        parser.add_argument('--include', action=AppendFilter, nargs=1,
                            dest='path')
        parser.add_argument('--exclude', action=AppendFilter, nargs=1,
                            dest='path')
        parsed_args = parser.parse_args(['--include', 'a', '--exclude', 'b'])
        self.assertEqual(parsed_args.path, [['--include', 'a'],
                                            ['--exclude', 'b']])


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


class TestCreateWarning(unittest.TestCase):
    def test_create_warning(self):
        path = '/foo/'
        error_message = 'There was an error'
        warning_message = create_warning(path, error_message)
        self.assertEqual(warning_message.message,
                         'warning: Skipping file /foo/. There was an error')
        self.assertFalse(warning_message.error)
        self.assertTrue(warning_message.warning)


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
        size = 5 * (1024 ** 4)
        # If we try to upload a 5TB file, we'll need to use 896MB part
        # sizes.
        self.assertEqual(find_chunksize(size, chunksize), 896 * (1024 ** 2))

    def test_super_chunk(self):
        """
        This tests to ensure that the ``chunksize can never be larger than
        the ``MAX_SINGLE_UPLOAD_SIZE``
        """
        chunksize = MAX_SINGLE_UPLOAD_SIZE + 1
        size = MAX_SINGLE_UPLOAD_SIZE * 2
        self.assertEqual(find_chunksize(size, chunksize),
                         MAX_SINGLE_UPLOAD_SIZE)


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

    def test_reset_stream_emulation(self):
        filename = os.path.join(self.tempdir, 'foo')
        f = open(filename, 'wb')
        f.write(b'onetwothreefourfivesixseveneightnineten')
        f.flush()
        chunk = ReadFileChunk(filename, start_byte=11, size=4)
        self.assertEqual(chunk.read(), b'four')
        chunk.seek(0)
        self.assertEqual(chunk.read(), b'four')

    def test_read_past_end_of_file(self):
        filename = os.path.join(self.tempdir, 'foo')
        f = open(filename, 'wb')
        f.write(b'onetwothreefourfivesixseveneightnineten')
        f.flush()
        chunk = ReadFileChunk(filename, start_byte=36, size=100000)
        self.assertEqual(chunk.read(), b'ten')
        self.assertEqual(chunk.read(), b'')
        self.assertEqual(len(chunk), 3)

    def test_tell_and_seek(self):
        filename = os.path.join(self.tempdir, 'foo')
        f = open(filename, 'wb')
        f.write(b'onetwothreefourfivesixseveneightnineten')
        f.flush()
        chunk = ReadFileChunk(filename, start_byte=36, size=100000)
        self.assertEqual(chunk.tell(), 0)
        self.assertEqual(chunk.read(), b'ten')
        self.assertEqual(chunk.tell(), 3)
        chunk.seek(0)
        self.assertEqual(chunk.tell(), 0)


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


class TestStablePriorityQueue(unittest.TestCase):
    def test_fifo_order_of_same_priorities(self):
        a = mock.Mock()
        a.PRIORITY = 5
        b = mock.Mock()
        b.PRIORITY = 5
        c = mock.Mock()
        c.PRIORITY = 1

        q = StablePriorityQueue(maxsize=10, max_priority=20)
        q.put(a)
        q.put(b)
        q.put(c)

        # First we should get c because it's the lowest priority.
        # We're using assertIs because we want the *exact* object.
        self.assertIs(q.get(), c)
        # Then a and b are the same priority, but we should get
        # a first because it was inserted first.
        self.assertIs(q.get(), a)
        self.assertIs(q.get(), b)

    def test_queue_length(self):
        a = mock.Mock()
        a.PRIORITY = 5

        q = StablePriorityQueue(maxsize=10, max_priority=20)
        self.assertEqual(q.qsize(), 0)

        q.put(a)
        self.assertEqual(q.qsize(), 1)

        q.get()
        self.assertEqual(q.qsize(), 0)

    def test_insert_max_priority_capped(self):
        q = StablePriorityQueue(maxsize=10, max_priority=20)
        a = mock.Mock()
        a.PRIORITY = 100
        q.put(a)

        self.assertIs(q.get(), a)

    def test_priority_attr_is_missing(self):
        # If priority attr is missing, we should add it
        # to the lowest priority.
        q = StablePriorityQueue(maxsize=10, max_priority=20)
        a = object()
        b = mock.Mock()
        b.PRIORITY = 5

        q.put(a)
        q.put(b)

        self.assertIs(q.get(), b)
        self.assertIs(q.get(), a)


class TestBucketList(unittest.TestCase):
    def setUp(self):
        self.operation = mock.Mock()
        self.emitter = HierarchicalEmitter()
        self.operation.session.register = self.emitter.register
        self.operation.session.unregister = self.emitter.unregister
        self.endpoint = mock.sentinel.endpoint
        self.date_parser = mock.Mock()
        self.date_parser.return_value = mock.sentinel.now
        self.responses = []

    def fake_paginate(self, *args, **kwargs):
        for response in self.responses:
            self.emitter.emit('after-call.s3.ListObjects', parsed=response[1])
        return self.responses

    def test_list_objects(self):
        now = mock.sentinel.now
        self.operation.paginate = self.fake_paginate
        self.responses = [
            (None, {'Contents': [
                {'LastModified': '2014-02-27T04:20:38.000Z',
                 'Key': 'a', 'Size': 1},
                {'LastModified': '2014-02-27T04:20:38.000Z',
                 'Key': 'b', 'Size': 2},]}),
            (None, {'Contents': [
                {'LastModified': '2014-02-27T04:20:38.000Z',
                 'Key': 'c', 'Size': 3},
            ]}),
        ]
        lister = BucketLister(self.operation, self.endpoint, self.date_parser)
        objects = list(lister.list_objects(bucket='foo'))
        self.assertEqual(objects, [('foo/a', 1, now), ('foo/b', 2, now),
                                   ('foo/c', 3, now)])

    def test_urlencoded_keys(self):
        # In order to workaround control chars being in key names,
        # we force the urlencoding of the key names and we decode
        # them before yielding them.  For example, note the %0D
        # in bar.txt:
        now = mock.sentinel.now
        self.operation.paginate = self.fake_paginate
        self.responses = [
            (None, {'Contents': [
                {'LastModified': '2014-02-27T04:20:38.000Z',
                 'Key': 'bar%0D.txt', 'Size': 1}]}),
        ]
        lister = BucketLister(self.operation, self.endpoint, self.date_parser)
        objects = list(lister.list_objects(bucket='foo'))
        # And note how it's been converted to '\r'.
        self.assertEqual(objects, [('foo/bar\r.txt', 1, now)])

    def test_urlencoded_with_unicode_keys(self):
        now = mock.sentinel.now
        self.operation.paginate = self.fake_paginate
        self.responses = [
            (None, {'Contents': [
                {'LastModified': '2014-02-27T04:20:38.000Z',
                 'Key': '%E2%9C%93', 'Size': 1}]}),
        ]
        lister = BucketLister(self.operation, self.endpoint, self.date_parser)
        objects = list(lister.list_objects(bucket='foo'))
        # And note how it's been converted to '\r'.
        self.assertEqual(objects, [(u'foo/\u2713', 1, now)])


class TestScopedEventHandler(unittest.TestCase):
    def test_scoped_session_handler(self):
        session = mock.Mock()
        scoped = ScopedEventHandler(session, 'eventname', 'handler')
        with scoped:
            session.register.assert_called_with('eventname', 'handler', None,
                                                False)
        session.unregister.assert_called_with('eventname', 'handler', None,
                                              False)

    def test_scoped_session_unique(self):
        session = mock.Mock()
        scoped = ScopedEventHandler(session, 'eventname', 'handler', 'unique')
        with scoped:
            session.register.assert_called_with('eventname', 'handler',
                                                'unique', False)
        session.unregister.assert_called_with('eventname', 'handler', 'unique',
                                              False)


class TestGetFileStat(unittest.TestCase):

    def test_get_file_stat(self):
        now = datetime.datetime.now(tzlocal())
        epoch_now = time.mktime(now.timetuple())
        with temporary_file('w') as f:
            f.write('foo')
            f.flush()
            os.utime(f.name, (epoch_now, epoch_now))
            size, update_time = get_file_stat(f.name)
            self.assertEqual(size, 3)
            self.assertEqual(time.mktime(update_time.timetuple()), epoch_now)

    def test_get_file_stat_error_message(self):
        patch_attribute = 'awscli.customizations.s3.utils.datetime'
        with mock.patch(patch_attribute) as f:
            with mock.patch('os.stat'):
                f.fromtimestamp.side_effect = ValueError(
                    "timestamp out of range for platform "
                    "localtime()/gmtime() function")
                with self.assertRaisesRegexp(
                    ValueError, 'myfilename\.txt'):
                    get_file_stat('myfilename.txt')


if __name__ == "__main__":
    unittest.main()

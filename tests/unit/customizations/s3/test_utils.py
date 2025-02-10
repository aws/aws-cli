# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from awscli.testutils import mock, unittest, temporary_file
import argparse
import errno
import os
import tempfile
import shutil
import ntpath
import time
import datetime

import pytest
from dateutil.tz import tzlocal
from s3transfer.futures import TransferMeta, TransferFuture
from s3transfer.compat import seekable
from botocore.hooks import HierarchicalEmitter

from awscli.compat import queue
from awscli.compat import StringIO
from awscli.testutils import FileCreator
from awscli.customizations.s3.utils import (
    find_bucket_key,
    guess_content_type, relative_path, block_unsupported_resources,
    StablePriorityQueue, BucketLister, get_file_stat, AppendFilter,
    create_warning, human_readable_size, human_readable_to_bytes,
    set_file_utime, SetFileUtimeError, RequestParamsMapper, StdoutBytesWriter,
    ProvideSizeSubscriber, OnDoneFilteredSubscriber,
    ProvideUploadContentTypeSubscriber, ProvideCopyContentTypeSubscriber,
    ProvideLastModifiedTimeSubscriber, DirectoryCreatorSubscriber,
    DeleteSourceObjectSubscriber, DeleteSourceFileSubscriber,
    DeleteCopySourceObjectSubscriber, NonSeekableStream, CreateDirectoryError,
    S3PathResolver)
from awscli.customizations.s3.results import WarningResult
from tests.unit.customizations.s3 import FakeTransferFuture
from tests.unit.customizations.s3 import FakeTransferFutureMeta
from tests.unit.customizations.s3 import FakeTransferFutureCallArgs


@pytest.fixture
def s3control_client():
    client = mock.MagicMock()
    client.get_access_point.return_value = {
        "Bucket": "mybucket"
    }
    client.list_multi_region_access_points.return_value = {
        "AccessPoints": [{
            "Alias": "myalias.mrap",
            "Regions": [{"Bucket": "mybucket"}]
        }]
    }
    return client


@pytest.fixture
def sts_client():
    client = mock.MagicMock()
    client.get_caller_identity.return_value = {
        "Account": "123456789012"
    }
    return client


@pytest.fixture
def s3_path_resolver(s3control_client, sts_client):
    return S3PathResolver(s3control_client, sts_client)


@pytest.mark.parametrize(
    'bytes_int, expected',
    (
        (1, '1 Byte'),
        (10, '10 Bytes'),
        (1000, '1000 Bytes'),
        (1024, '1.0 KiB'),
        (1024 ** 2, '1.0 MiB'),
        (1024 ** 3, '1.0 GiB'),
        (1024 ** 4, '1.0 TiB'),
        (1024 ** 5, '1.0 PiB'),
        (1024 ** 6, '1.0 EiB'),
        (1024 ** 2 - 1, '1.0 MiB'),
        (1024 ** 3 - 1, '1.0 GiB'),
    )
)
def test_human_readable_size(bytes_int, expected):
    assert human_readable_size(bytes_int) == expected


@pytest.mark.parametrize(
    'size_str, expected',
    (
        ("1", 1),
        ("1024", 1024),
        ("1KB", 1024),
        ("1kb", 1024),
        ("1MB", 1024 ** 2),
        ("1GB", 1024 ** 3),
        ("1TB", 1024 ** 4),
        ("1KiB", 1024),
        ("1kib", 1024),
        ("1MiB", 1024 ** 2),
        ("1GiB", 1024 ** 3),
        ("1TiB", 1024 ** 4),
    )
)
def test_convert_human_readable_to_bytes(size_str, expected):
    assert human_readable_to_bytes(size_str) == expected


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


class TestFindBucketKey(unittest.TestCase):
    def test_unicode(self):
        s3_path = '\u1234' + u'/' + '\u5678'
        bucket, key = find_bucket_key(s3_path)
        self.assertEqual(bucket, '\u1234')
        self.assertEqual(key, '\u5678')

    def test_bucket(self):
        bucket, key = find_bucket_key('bucket')
        self.assertEqual(bucket, 'bucket')
        self.assertEqual(key, '')

    def test_bucket_with_slash(self):
        bucket, key = find_bucket_key('bucket/')
        self.assertEqual(bucket, 'bucket')
        self.assertEqual(key, '')

    def test_bucket_with_key(self):
        bucket, key = find_bucket_key('bucket/key')
        self.assertEqual(bucket, 'bucket')
        self.assertEqual(key, 'key')

    def test_bucket_with_key_and_prefix(self):
        bucket, key = find_bucket_key('bucket/prefix/key')
        self.assertEqual(bucket, 'bucket')
        self.assertEqual(key, 'prefix/key')

    def test_accesspoint_arn(self):
        bucket, key = find_bucket_key(
            'arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint')
        self.assertEqual(
            bucket, 'arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint')
        self.assertEqual(key, '')

    def test_accesspoint_arn_with_slash(self):
        bucket, key = find_bucket_key(
            'arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint/')
        self.assertEqual(
            bucket, 'arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint')
        self.assertEqual(key, '')

    def test_accesspoint_arn_with_key(self):
        bucket, key = find_bucket_key(
            'arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint/key')
        self.assertEqual(
            bucket, 'arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint')
        self.assertEqual(key, 'key')

    def test_accesspoint_arn_with_key_and_prefix(self):
        bucket, key = find_bucket_key(
            'arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint/pre/key')
        self.assertEqual(
            bucket, 'arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint')
        self.assertEqual(key, 'pre/key')

    def test_outpost_arn_with_colon(self):
        bucket, key = find_bucket_key(
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:'
            'accesspoint:my-accesspoint'
        )
        self.assertEqual(
            bucket,
            (
                'arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:'
                'accesspoint:my-accesspoint'
            )
        )
        self.assertEqual(key, '')

    def test_outpost_arn_with_colon_and_key(self):
        bucket, key = find_bucket_key(
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:'
            'accesspoint:my-accesspoint/key'
        )
        self.assertEqual(
            bucket,
            (
                'arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:'
                'accesspoint:my-accesspoint'
            )
        )
        self.assertEqual(key, 'key')

    def test_outpost_arn_with_colon_and_key_with_colon_in_name(self):
        bucket, key = find_bucket_key(
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:'
            'accesspoint:my-accesspoint/key:name'
        )
        self.assertEqual(
            bucket,
            (
                'arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:'
                'accesspoint:my-accesspoint'
            )
        )
        self.assertEqual(key, 'key:name')

    def test_outpost_arn_with_colon_and_key_with_slash_in_name(self):
        bucket, key = find_bucket_key(
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:'
            'accesspoint:my-accesspoint/key/name'
        )
        self.assertEqual(
            bucket,
            (
                'arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:'
                'accesspoint:my-accesspoint'
            )
        )
        self.assertEqual(key, 'key/name')

    def test_outpost_arn_with_colon_and_key_with_slash_and_colon_in_name(self):
        bucket, key = find_bucket_key(
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:'
            'accesspoint:my-accesspoint/prefix/key:name'
        )
        self.assertEqual(
            bucket,
            (
                'arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-12334:'
                'accesspoint:my-accesspoint'
            )
        )
        self.assertEqual(key, 'prefix/key:name')

    def test_outpost_arn_with_slash(self):
        bucket, key = find_bucket_key(
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost/op-12334/'
            'accesspoint/my-accesspoint'
        )
        self.assertEqual(
            bucket,
            (
                'arn:aws:s3-outposts:us-west-2:123456789012:outpost/op-12334/'
                'accesspoint/my-accesspoint'
            )
        )
        self.assertEqual(key, '')

    def test_outpost_arn_with_slash_and_key(self):
        bucket, key = find_bucket_key(
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost/op-12334/'
            'accesspoint/my-accesspoint/key'
        )
        self.assertEqual(
            bucket,
            (
                'arn:aws:s3-outposts:us-west-2:123456789012:outpost/op-12334/'
                'accesspoint/my-accesspoint'
            )
        )
        self.assertEqual(key, 'key')

    def test_outpost_arn_with_slash_and_key_with_colon_in_name(self):
        bucket, key = find_bucket_key(
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost/op-12334/'
            'accesspoint/my-accesspoint/key:name'
        )
        self.assertEqual(
            bucket,
            (
                'arn:aws:s3-outposts:us-west-2:123456789012:outpost/op-12334/'
                'accesspoint/my-accesspoint'
            )
        )
        self.assertEqual(key, 'key:name')

    def test_outpost_arn_with_slash_and_key_with_slash_in_name(self):
        bucket, key = find_bucket_key(
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost/op-12334/'
            'accesspoint/my-accesspoint/key/name'
        )
        self.assertEqual(
            bucket,
            (
                'arn:aws:s3-outposts:us-west-2:123456789012:outpost/op-12334/'
                'accesspoint/my-accesspoint'
            )
        )
        self.assertEqual(key, 'key/name')

    def test_outpost_arn_with_slash_and_key_with_slash_and_colon_in_name(self):
        bucket, key = find_bucket_key(
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost/op-12334/'
            'accesspoint/my-accesspoint/prefix/key:name'
        )
        self.assertEqual(
            bucket,
            (
                'arn:aws:s3-outposts:us-west-2:123456789012:outpost/op-12334/'
                'accesspoint/my-accesspoint'
            )
        )
        self.assertEqual(key, 'prefix/key:name')


class TestBlockUnsupportedResources(unittest.TestCase):
    def test_object_lambda_arn_with_colon_raises_exception(self):
        with self.assertRaisesRegex(
                ValueError, 'Use s3api commands instead'):
            block_unsupported_resources(
                'arn:aws:s3-object-lambda:us-west-2:123456789012:'
                'accesspoint:my-accesspoint'
            )

    def test_object_lambda_arn_with_slash_raises_exception(self):
        with self.assertRaisesRegex(
                ValueError, 'Use s3api commands instead'):
            block_unsupported_resources(
                 'arn:aws:s3-object-lambda:us-west-2:123456789012:'
                 'accesspoint/my-accesspoint'
            )

    def test_outpost_bucket_arn_with_colon_raises_exception(self):
        with self.assertRaisesRegex(
                ValueError, 'Use s3control commands instead'):
            block_unsupported_resources(
                'arn:aws:s3-outposts:us-west-2:123456789012:'
                'outpost/op-0a12345678abcdefg:bucket/bucket-foo'
            )

    def test_outpost_bucket_arn_with_slash_raises_exception(self):
        with self.assertRaisesRegex(
                ValueError, 'Use s3control commands instead'):
            block_unsupported_resources(
                 'arn:aws:s3-outposts:us-west-2:123456789012:'
                 'outpost/op-0a12345678abcdefg/bucket/bucket-foo'
            )


class TestCreateWarning(unittest.TestCase):
    def test_create_warning(self):
        path = '/foo/'
        error_message = 'There was an error'
        warning_message = create_warning(path, error_message)
        self.assertEqual(warning_message.message,
                         'warning: Skipping file /foo/. There was an error')
        self.assertFalse(warning_message.error)
        self.assertTrue(warning_message.warning)


class TestGuessContentType(unittest.TestCase):
    def test_guess_content_type(self):
        self.assertEqual(guess_content_type('foo.txt'), 'text/plain')

    def test_guess_content_type_with_no_valid_matches(self):
        self.assertEqual(guess_content_type('no-extension'), None)

    def test_guess_content_type_with_unicode_error_returns_no_match(self):
        with mock.patch('mimetypes.guess_type') as guess_type_patch:
            # This should throw a UnicodeDecodeError.
            guess_type_patch.side_effect = lambda x: b'\xe2'.decode('ascii')
            self.assertEqual(guess_content_type('foo.txt'), None)


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
        self.client = mock.Mock()
        self.emitter = HierarchicalEmitter()
        self.client.meta.events = self.emitter
        self.date_parser = mock.Mock()
        self.date_parser.return_value = mock.sentinel.now
        self.responses = []

    def fake_paginate(self, *args, **kwargs):
        for response in self.responses:
            self.emitter.emit('after-call.s3.ListObjectsV2', parsed=response)
        return self.responses

    def test_list_objects(self):
        now = mock.sentinel.now
        self.client.get_paginator.return_value.paginate = self.fake_paginate
        individual_response_elements = [
            {'LastModified': '2014-02-27T04:20:38.000Z',
             'Key': 'a', 'Size': 1},
            {'LastModified': '2014-02-27T04:20:38.000Z',
                 'Key': 'b', 'Size': 2},
            {'LastModified': '2014-02-27T04:20:38.000Z',
                 'Key': 'c', 'Size': 3}
        ]
        self.responses = [
            {'Contents': individual_response_elements[0:2]},
            {'Contents': [individual_response_elements[2]]}
        ]
        lister = BucketLister(self.client, self.date_parser)
        objects = list(lister.list_objects(bucket='foo'))
        self.assertEqual(objects,
            [('foo/a', individual_response_elements[0]),
             ('foo/b', individual_response_elements[1]),
             ('foo/c', individual_response_elements[2])])
        for individual_response in individual_response_elements:
            self.assertEqual(individual_response['LastModified'], now)

    def test_list_objects_passes_in_extra_args(self):
        self.client.get_paginator.return_value.paginate.return_value = [
            {'Contents': [
                {'LastModified': '2014-02-27T04:20:38.000Z',
                 'Key': 'mykey', 'Size': 3}
            ]}
        ]
        lister = BucketLister(self.client, self.date_parser)
        list(
            lister.list_objects(
                bucket='mybucket', extra_args={'RequestPayer': 'requester'}
            )
        )
        self.client.get_paginator.return_value.paginate.assert_called_with(
            Bucket='mybucket', PaginationConfig={'PageSize': None},
            RequestPayer='requester'
        )


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

    def test_error_message(self):
        with mock.patch('os.stat', mock.Mock(side_effect=IOError('msg'))):
            with self.assertRaisesRegex(ValueError, r'myfilename\.txt'):
                get_file_stat('myfilename.txt')

    def assert_handles_fromtimestamp_error(self, error):
        patch_attribute = 'awscli.customizations.s3.utils.datetime'
        with mock.patch(patch_attribute) as datetime_mock:
            with temporary_file('w') as temp_file:
                temp_file.write('foo')
                temp_file.flush()
                datetime_mock.fromtimestamp.side_effect = error
                size, update_time = get_file_stat(temp_file.name)
                self.assertIsNone(update_time)

    def test_returns_epoch_on_invalid_timestamp(self):
        self.assert_handles_fromtimestamp_error(ValueError())

    def test_returns_epoch_on_invalid_timestamp_os_error(self):
        self.assert_handles_fromtimestamp_error(OSError())

    def test_returns_epoch_on_invalid_timestamp_overflow_error(self):
        self.assert_handles_fromtimestamp_error(OverflowError())


class TestSetsFileUtime(unittest.TestCase):

    def test_successfully_sets_utime(self):
        now = datetime.datetime.now(tzlocal())
        epoch_now = time.mktime(now.timetuple())
        with temporary_file('w') as f:
            set_file_utime(f.name, epoch_now)
            _, update_time = get_file_stat(f.name)
            self.assertEqual(time.mktime(update_time.timetuple()), epoch_now)

    def test_throws_more_relevant_error_when_errno_1(self):
        now = datetime.datetime.now(tzlocal())
        epoch_now = time.mktime(now.timetuple())
        with mock.patch('os.utime') as utime_mock:
            utime_mock.side_effect = OSError(1, '')
            with self.assertRaises(SetFileUtimeError):
                set_file_utime('not_real_file', epoch_now)

    def test_passes_through_other_os_errors(self):
        now = datetime.datetime.now(tzlocal())
        epoch_now = time.mktime(now.timetuple())
        with mock.patch('os.utime') as utime_mock:
            utime_mock.side_effect = OSError(2, '')
            with self.assertRaises(OSError):
                set_file_utime('not_real_file', epoch_now)


class TestRequestParamsMapperSSE(unittest.TestCase):
    def setUp(self):
        self.cli_params = {
            'sse': 'AES256',
            'sse_kms_key_id': 'my-kms-key',
            'sse_c': 'AES256',
            'sse_c_key': 'my-sse-c-key',
            'sse_c_copy_source': 'AES256',
            'sse_c_copy_source_key': 'my-sse-c-copy-source-key'
        }

    def test_head_object(self):
        params = {}
        RequestParamsMapper.map_head_object_params(params, self.cli_params)
        self.assertEqual(
            params,
            {'SSECustomerAlgorithm': 'AES256',
             'SSECustomerKey': 'my-sse-c-key'}
        )

    def test_put_object(self):
        params = {}
        RequestParamsMapper.map_put_object_params(params, self.cli_params)
        self.assertEqual(
            params,
            {'SSECustomerAlgorithm': 'AES256',
             'SSECustomerKey': 'my-sse-c-key',
             'SSEKMSKeyId': 'my-kms-key',
             'ServerSideEncryption': 'AES256'}
        )

    def test_get_object(self):
        params = {}
        RequestParamsMapper.map_get_object_params(params, self.cli_params)
        self.assertEqual(
            params,
            {'SSECustomerAlgorithm': 'AES256',
             'SSECustomerKey': 'my-sse-c-key'}
        )

    def test_copy_object(self):
        params = {}
        RequestParamsMapper.map_copy_object_params(params, self.cli_params)
        self.assertEqual(
            params,
            {'CopySourceSSECustomerAlgorithm': 'AES256',
             'CopySourceSSECustomerKey': 'my-sse-c-copy-source-key',
             'SSECustomerAlgorithm': 'AES256',
             'SSECustomerKey': 'my-sse-c-key',
             'SSEKMSKeyId': 'my-kms-key',
             'ServerSideEncryption': 'AES256'}
        )

    def test_create_multipart_upload(self):
        params = {}
        RequestParamsMapper.map_create_multipart_upload_params(
            params, self.cli_params)
        self.assertEqual(
            params,
            {'SSECustomerAlgorithm': 'AES256',
             'SSECustomerKey': 'my-sse-c-key',
             'SSEKMSKeyId': 'my-kms-key',
             'ServerSideEncryption': 'AES256'}
        )

    def test_upload_part(self):
        params = {}
        RequestParamsMapper.map_upload_part_params(params, self.cli_params)
        self.assertEqual(
            params,
            {'SSECustomerAlgorithm': 'AES256',
             'SSECustomerKey': 'my-sse-c-key'}
        )

    def test_upload_part_copy(self):
        params = {}
        RequestParamsMapper.map_upload_part_copy_params(
            params, self.cli_params)
        self.assertEqual(
            params,
            {'CopySourceSSECustomerAlgorithm': 'AES256',
             'CopySourceSSECustomerKey': 'my-sse-c-copy-source-key',
             'SSECustomerAlgorithm': 'AES256',
             'SSECustomerKey': 'my-sse-c-key'})


class TestRequestParamsMapperChecksumAlgorithm:
    @pytest.fixture
    def cli_params(self):
        return {'checksum_algorithm': 'CRC32'}

    @pytest.fixture
    def cli_params_no_algorithm(self):
        return {}

    def test_put_object(self, cli_params):
        request_params = {}
        RequestParamsMapper.map_put_object_params(request_params, cli_params)
        assert request_params == {'ChecksumAlgorithm': 'CRC32'}

    def test_put_object_no_checksum(self, cli_params_no_algorithm):
        request_params = {}
        RequestParamsMapper.map_put_object_params(request_params, cli_params_no_algorithm)
        assert 'ChecksumAlgorithm' not in request_params

    def test_copy_object(self, cli_params):
        request_params = {}
        RequestParamsMapper.map_copy_object_params(request_params, cli_params)
        assert request_params == {'ChecksumAlgorithm': 'CRC32'}

    def test_copy_object_no_checksum(self, cli_params_no_algorithm):
        request_params = {}
        RequestParamsMapper.map_put_object_params(request_params, cli_params_no_algorithm)
        assert 'ChecksumAlgorithm' not in request_params


class TestRequestParamsMapperChecksumMode:
    @pytest.fixture
    def cli_params(self):
        return {'checksum_mode': 'ENABLED'}

    @pytest.fixture
    def cli_params_no_checksum(self):
        return {}

    def test_get_object(self, cli_params):
        request_params = {}
        RequestParamsMapper.map_get_object_params(request_params, cli_params)
        assert request_params == {'ChecksumMode': 'ENABLED'}

    def test_get_object_no_checksums(self, cli_params_no_checksum):
        request_params = {}
        RequestParamsMapper.map_get_object_params(request_params, cli_params_no_checksum)
        assert 'ChecksumMode' not in request_params


class TestRequestParamsMapperRequestPayer(unittest.TestCase):
    def setUp(self):
        self.cli_params = {'request_payer': 'requester'}

    def test_head_object(self):
        params = {}
        RequestParamsMapper.map_head_object_params(params, self.cli_params)
        self.assertEqual(params, {'RequestPayer': 'requester'})

    def test_put_object(self):
        params = {}
        RequestParamsMapper.map_put_object_params(params, self.cli_params)
        self.assertEqual(params, {'RequestPayer': 'requester'})

    def test_get_object(self):
        params = {}
        RequestParamsMapper.map_get_object_params(params, self.cli_params)
        self.assertEqual(params, {'RequestPayer': 'requester'})

    def test_copy_object(self):
        params = {}
        RequestParamsMapper.map_copy_object_params(params, self.cli_params)
        self.assertEqual(params, {'RequestPayer': 'requester'})

    def test_create_multipart_upload(self):
        params = {}
        RequestParamsMapper.map_create_multipart_upload_params(
            params, self.cli_params)
        self.assertEqual(params, {'RequestPayer': 'requester'})

    def test_upload_part(self):
        params = {}
        RequestParamsMapper.map_upload_part_params(params, self.cli_params)
        self.assertEqual(params, {'RequestPayer': 'requester'})

    def test_upload_part_copy(self):
        params = {}
        RequestParamsMapper.map_upload_part_copy_params(
            params, self.cli_params)
        self.assertEqual(params, {'RequestPayer': 'requester'})

    def test_delete_object(self):
        params = {}
        RequestParamsMapper.map_delete_object_params(
            params, self.cli_params)
        self.assertEqual(params, {'RequestPayer': 'requester'})

    def test_list_objects(self):
        params = {}
        RequestParamsMapper.map_list_objects_v2_params(
            params, self.cli_params)
        self.assertEqual(params, {'RequestPayer': 'requester'})


class TestBytesPrint(unittest.TestCase):
    def setUp(self):
        self.stdout = mock.Mock()
        self.stdout.buffer = self.stdout

    def test_stdout_wrapper(self):
        wrapper = StdoutBytesWriter(self.stdout)
        wrapper.write(b'foo')
        self.assertTrue(self.stdout.write.called)
        self.assertEqual(self.stdout.write.call_args[0][0], b'foo')


class TestProvideSizeSubscriber(unittest.TestCase):
    def setUp(self):
        self.transfer_future = mock.Mock(spec=TransferFuture)
        self.transfer_meta = TransferMeta()
        self.transfer_future.meta = self.transfer_meta

    def test_size_set(self):
        self.transfer_meta.provide_transfer_size(5)
        subscriber = ProvideSizeSubscriber(10)
        subscriber.on_queued(self.transfer_future)
        self.assertEqual(self.transfer_meta.size, 10)


class OnDoneFilteredRecordingSubscriber(OnDoneFilteredSubscriber):
    def __init__(self):
        self.on_success_calls = []
        self.on_failure_calls = []

    def _on_success(self, future):
        self.on_success_calls.append(future)

    def _on_failure(self, future, exception):
        self.on_failure_calls.append((future, exception))


class TestOnDoneFilteredSubscriber(unittest.TestCase):
    def test_on_success(self):
        subscriber = OnDoneFilteredRecordingSubscriber()
        future = FakeTransferFuture('return-value')
        subscriber.on_done(future)
        self.assertEqual(subscriber.on_success_calls, [future])
        self.assertEqual(subscriber.on_failure_calls, [])

    def test_on_failure(self):
        subscriber = OnDoneFilteredRecordingSubscriber()
        exception = Exception('my exception')
        future = FakeTransferFuture(exception=exception)
        subscriber.on_done(future)
        self.assertEqual(subscriber.on_failure_calls, [(future, exception)])
        self.assertEqual(subscriber.on_success_calls, [])


class TestProvideUploadContentTypeSubscriber(unittest.TestCase):
    def setUp(self):
        self.filename = 'myfile.txt'
        self.extra_args = {}
        self.future = self.set_future()
        self.subscriber = ProvideUploadContentTypeSubscriber()

    def set_future(self):
        call_args = FakeTransferFutureCallArgs(
            fileobj=self.filename, extra_args=self.extra_args)
        meta = FakeTransferFutureMeta(call_args=call_args)
        return FakeTransferFuture(meta=meta)

    def test_on_queued_provides_content_type(self):
        self.subscriber.on_queued(self.future)
        self.assertEqual(self.extra_args, {'ContentType': 'text/plain'})

    def test_on_queued_does_not_provide_content_type_when_unknown(self):
        self.filename = 'file-with-no-extension'
        self.future = self.set_future()
        self.subscriber.on_queued(self.future)
        self.assertEqual(self.extra_args, {})


class TestProvideCopyContentTypeSubscriber(
        TestProvideUploadContentTypeSubscriber):
    def setUp(self):
        self.filename = 'myfile.txt'
        self.extra_args = {}
        self.future = self.set_future()
        self.subscriber = ProvideCopyContentTypeSubscriber()

    def set_future(self):
        copy_source = {'Bucket': 'mybucket', 'Key': self.filename}
        call_args = FakeTransferFutureCallArgs(
            copy_source=copy_source, extra_args=self.extra_args)
        meta = FakeTransferFutureMeta(call_args=call_args)
        return FakeTransferFuture(meta=meta)


class BaseTestWithFileCreator(unittest.TestCase):
    def setUp(self):
        self.file_creator = FileCreator()

    def tearDown(self):
        self.file_creator.remove_all()


class TestProvideLastModifiedTimeSubscriber(BaseTestWithFileCreator):
    def setUp(self):
        super(TestProvideLastModifiedTimeSubscriber, self).setUp()
        self.filename = self.file_creator.create_file('myfile', 'my contents')
        self.desired_utime = datetime.datetime(
            2016, 1, 18, 7, 0, 0, tzinfo=tzlocal())
        self.result_queue = queue.Queue()
        self.subscriber = ProvideLastModifiedTimeSubscriber(
            self.desired_utime, self.result_queue)

        call_args = FakeTransferFutureCallArgs(fileobj=self.filename)
        meta = FakeTransferFutureMeta(call_args=call_args)
        self.future = FakeTransferFuture(meta=meta)

    def test_on_success_modifies_utime(self):
        self.subscriber.on_done(self.future)
        _, utime = get_file_stat(self.filename)
        self.assertEqual(utime, self.desired_utime)

    def test_on_success_failure_in_utime_mod_raises_warning(self):
        self.subscriber = ProvideLastModifiedTimeSubscriber(
            None, self.result_queue)
        self.subscriber.on_done(self.future)
        # Because the time to provide was None it will throw an exception
        # which results in the a warning about the utime not being able
        # to be set being placed in the result queue.
        result = self.result_queue.get()
        self.assertIsInstance(result, WarningResult)
        self.assertIn(
            'unable to update the last modified time', result.message)


class TestDirectoryCreatorSubscriber(BaseTestWithFileCreator):
    def setUp(self):
        super(TestDirectoryCreatorSubscriber, self).setUp()
        self.directory_to_create = os.path.join(
            self.file_creator.rootdir, 'new-directory')
        self.filename = os.path.join(self.directory_to_create, 'myfile')

        call_args = FakeTransferFutureCallArgs(fileobj=self.filename)
        meta = FakeTransferFutureMeta(call_args=call_args)
        self.future = FakeTransferFuture(meta=meta)

        self.subscriber = DirectoryCreatorSubscriber()

    def test_on_queued_creates_directories_if_do_not_exist(self):
        self.subscriber.on_queued(self.future)
        self.assertTrue(os.path.exists(self.directory_to_create))

    def test_on_queued_does_not_create_directories_if_exist(self):
        os.makedirs(self.directory_to_create)
        # This should not cause any issues if the directory already exists
        self.subscriber.on_queued(self.future)
        # The directory should still exist
        self.assertTrue(os.path.exists(self.directory_to_create))

    def test_on_queued_failure_propagates_create_directory_error(self):
        # If makedirs() raises an OSError of exception, we should
        # propagate the exception with a better worded CreateDirectoryError.
        with mock.patch('os.makedirs') as makedirs_patch:
            makedirs_patch.side_effect = OSError()
            with self.assertRaises(CreateDirectoryError):
                self.subscriber.on_queued(self.future)
        self.assertFalse(os.path.exists(self.directory_to_create))

    def test_on_queued_failure_propagates_clear_error_message(self):
        # If makedirs() raises an OSError of exception, we should
        # propagate the exception.
        with mock.patch('os.makedirs') as makedirs_patch:
            os_error = OSError()
            os_error.errno = errno.EEXIST
            makedirs_patch.side_effect = os_error
            # The on_queued should not raise an error if the directory
            # already exists
            try:
                self.subscriber.on_queued(self.future)
            except Exception as e:
                self.fail(
                    'on_queued should not have raised an exception related '
                    'to directory creation especially if one already existed '
                    'but got %s' % e)


class TestDeleteSourceObjectSubscriber(unittest.TestCase):
    def setUp(self):
        self.client = mock.Mock()
        self.bucket = 'mybucket'
        self.key = 'mykey'
        call_args = FakeTransferFutureCallArgs(
            bucket=self.bucket, key=self.key, extra_args={})
        meta = FakeTransferFutureMeta(call_args=call_args)
        self.future = mock.Mock()
        self.future.meta = meta

    def test_deletes_object(self):
        DeleteSourceObjectSubscriber(self.client).on_done(self.future)
        self.client.delete_object.assert_called_once_with(
            Bucket=self.bucket, Key=self.key)
        self.future.set_exception.assert_not_called()

    def test_sets_exception_on_error(self):
        exception = ValueError()
        self.client.delete_object.side_effect = exception
        DeleteSourceObjectSubscriber(self.client).on_done(self.future)
        self.client.delete_object.assert_called_once_with(
            Bucket=self.bucket, Key=self.key)
        self.future.set_exception.assert_called_once_with(exception)

    def test_with_request_payer(self):
        self.future.meta.call_args.extra_args = {'RequestPayer': 'requester'}
        DeleteSourceObjectSubscriber(self.client).on_done(self.future)
        self.client.delete_object.assert_called_once_with(
            Bucket=self.bucket, Key=self.key, RequestPayer='requester')


class TestDeleteCopySourceObjectSubscriber(unittest.TestCase):
    def setUp(self):
        self.client = mock.Mock()
        self.bucket = 'mybucket'
        self.key = 'mykey'
        copy_source = {'Bucket': self.bucket, 'Key': self.key}
        call_args = FakeTransferFutureCallArgs(
            copy_source=copy_source, extra_args={})
        meta = FakeTransferFutureMeta(call_args=call_args)
        self.future = mock.Mock()
        self.future.meta = meta

    def test_deletes_object(self):
        DeleteCopySourceObjectSubscriber(self.client).on_done(self.future)
        self.client.delete_object.assert_called_once_with(
            Bucket=self.bucket, Key=self.key)
        self.future.set_exception.assert_not_called()

    def test_sets_exception_on_error(self):
        exception = ValueError()
        self.client.delete_object.side_effect = exception
        DeleteCopySourceObjectSubscriber(self.client).on_done(self.future)
        self.client.delete_object.assert_called_once_with(
            Bucket=self.bucket, Key=self.key)
        self.future.set_exception.assert_called_once_with(exception)

    def test_with_request_payer(self):
        self.future.meta.call_args.extra_args = {'RequestPayer': 'requester'}
        DeleteCopySourceObjectSubscriber(self.client).on_done(self.future)
        self.client.delete_object.assert_called_once_with(
            Bucket=self.bucket, Key=self.key, RequestPayer='requester')


class TestDeleteSourceFileSubscriber(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tempdir, 'myfile')
        call_args = FakeTransferFutureCallArgs(fileobj=self.filename)
        meta = FakeTransferFutureMeta(call_args=call_args)
        self.future = mock.Mock()
        self.future.meta = meta

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_deletes_file(self):
        with open(self.filename, 'w') as f:
            f.write('data')
        DeleteSourceFileSubscriber().on_done(self.future)
        self.assertFalse(os.path.exists(self.filename))
        self.future.set_exception.assert_not_called()

    def test_sets_exception_on_error(self):
        DeleteSourceFileSubscriber().on_done(self.future)
        self.assertFalse(os.path.exists(self.filename))
        call_args = self.future.set_exception.call_args[0]
        self.assertIsInstance(call_args[0], EnvironmentError)


class TestNonSeekableStream(unittest.TestCase):
    def test_can_make_stream_unseekable(self):
        fileobj = StringIO('foobar')
        self.assertTrue(seekable(fileobj))
        nonseekable_fileobj = NonSeekableStream(fileobj)
        self.assertFalse(seekable(nonseekable_fileobj))
        self.assertEqual(nonseekable_fileobj.read(), 'foobar')

    def test_can_specify_amount_for_nonseekable_stream(self):
        nonseekable_fileobj = NonSeekableStream(StringIO('foobar'))
        self.assertEqual(nonseekable_fileobj.read(3), 'foo')


class TestS3PathResolver:
    _BASE_ACCESSPOINT_ARN = (
        "s3://arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint")
    _BASE_OUTPOST_ACCESSPOINT_ARN = (
        "s3://arn:aws:s3-outposts:us-east-1:123456789012:outpost"
        "/op-foo/accesspoint/myaccesspoint")
    _BASE_ACCESSPOINT_ALIAS = "s3://myaccesspoint-foobar12345-s3alias"
    _BASE_OUTPOST_ACCESSPOINT_ALIAS = "s3://myaccesspoint-foobar12345--op-s3"
    _BASE_MRAP_ARN = "s3://arn:aws:s3::123456789012:accesspoint/myalias.mrap"

    @pytest.mark.parametrize(
        "path,resolved",
        [(_BASE_ACCESSPOINT_ARN,"s3://mybucket/"),
         (f"{_BASE_ACCESSPOINT_ARN}/","s3://mybucket/"),
         (f"{_BASE_ACCESSPOINT_ARN}/mykey","s3://mybucket/mykey"),
         (f"{_BASE_ACCESSPOINT_ARN}/myprefix/","s3://mybucket/myprefix/"),
         (f"{_BASE_ACCESSPOINT_ARN}/myprefix/mykey",
          "s3://mybucket/myprefix/mykey")]
    )
    def test_resolves_accesspoint_arn(
        self, path, resolved, s3_path_resolver, s3control_client
    ):
        resolved_paths = s3_path_resolver.resolve_underlying_s3_paths(path)
        assert resolved_paths == [resolved]
        s3control_client.get_access_point.assert_called_with(
            AccountId="123456789012",
            Name="myaccesspoint"
        )

    @pytest.mark.parametrize(
        "path,resolved",
        [(_BASE_OUTPOST_ACCESSPOINT_ARN,"s3://mybucket/"),
         (f"{_BASE_OUTPOST_ACCESSPOINT_ARN}/","s3://mybucket/"),
         (f"{_BASE_OUTPOST_ACCESSPOINT_ARN}/mykey","s3://mybucket/mykey"),
         (f"{_BASE_OUTPOST_ACCESSPOINT_ARN}/myprefix/",
          "s3://mybucket/myprefix/"),
         (f"{_BASE_OUTPOST_ACCESSPOINT_ARN}/myprefix/mykey",
          "s3://mybucket/myprefix/mykey")]
    )
    def test_resolves_outpost_accesspoint_arn(
        self, path, resolved, s3_path_resolver, s3control_client
    ):
        resolved_paths = s3_path_resolver.resolve_underlying_s3_paths(path)
        assert resolved_paths == [resolved]
        s3control_client.get_access_point.assert_called_with(
            AccountId="123456789012",
            Name=("arn:aws:s3-outposts:us-east-1:123456789012:outpost"
                  "/op-foo/accesspoint/myaccesspoint")
        )

    @pytest.mark.parametrize(
        "path,resolved",
        [(_BASE_ACCESSPOINT_ALIAS,"s3://mybucket/"),
         (f"{_BASE_ACCESSPOINT_ALIAS}/","s3://mybucket/"),
         (f"{_BASE_ACCESSPOINT_ALIAS}/mykey","s3://mybucket/mykey"),
         (f"{_BASE_ACCESSPOINT_ALIAS}/myprefix/","s3://mybucket/myprefix/"),
         (f"{_BASE_ACCESSPOINT_ALIAS}/myprefix/mykey",
          "s3://mybucket/myprefix/mykey")]
    )
    def test_resolves_accesspoint_alias(
        self, path, resolved, s3_path_resolver, s3control_client, sts_client
    ):
        resolved_paths = s3_path_resolver.resolve_underlying_s3_paths(path)
        assert resolved_paths == [resolved]
        sts_client.get_caller_identity.assert_called_once()
        s3control_client.get_access_point.assert_called_with(
            AccountId="123456789012",
            Name="myaccesspoint-foobar12345-s3alias"
        )

    @pytest.mark.parametrize(
        "path",
        [(_BASE_OUTPOST_ACCESSPOINT_ALIAS),
         (f"{_BASE_OUTPOST_ACCESSPOINT_ALIAS}/"),
         (f"{_BASE_OUTPOST_ACCESSPOINT_ALIAS}/mykey"),
         (f"{_BASE_OUTPOST_ACCESSPOINT_ALIAS}/myprefix/"),
         (f"{_BASE_OUTPOST_ACCESSPOINT_ALIAS}/myprefix/mykey")]
    )
    def test_outpost_accesspoint_alias_raises_exception(
        self, path, s3_path_resolver
    ):
        with pytest.raises(ValueError) as e:
            s3_path_resolver.resolve_underlying_s3_paths(path)
        assert "Can't resolve underlying bucket name" in str(e.value)

    @pytest.mark.parametrize(
        "path,resolved",
        [(_BASE_MRAP_ARN,"s3://mybucket/"),
         (f"{_BASE_MRAP_ARN}/","s3://mybucket/"),
         (f"{_BASE_MRAP_ARN}/mykey","s3://mybucket/mykey"),
         (f"{_BASE_MRAP_ARN}/myprefix/","s3://mybucket/myprefix/"),
         (f"{_BASE_MRAP_ARN}/myprefix/mykey","s3://mybucket/myprefix/mykey")]
    )
    def test_resolves_mrap_arn(
        self, path, resolved, s3_path_resolver, s3control_client
    ):
        resolved_paths = s3_path_resolver.resolve_underlying_s3_paths(path)
        assert resolved_paths == [resolved]
        s3control_client.list_multi_region_access_points.assert_called_with(
            AccountId="123456789012"
        )

    @pytest.mark.parametrize(
            "path,resolved,name",
            [(f"{_BASE_ACCESSPOINT_ARN}-s3alias/mykey","s3://mybucket/mykey",
              "myaccesspoint-s3alias"),
             (f"{_BASE_OUTPOST_ACCESSPOINT_ARN}--op-s3/mykey",
              "s3://mybucket/mykey",
              f"{_BASE_OUTPOST_ACCESSPOINT_ARN[5:]}--op-s3")]
    )
    def test_alias_suffixes_dont_match_accesspoint_arns(
        self, path, resolved, name, s3_path_resolver, s3control_client
    ):
        resolved_paths = s3_path_resolver.resolve_underlying_s3_paths(path)
        assert resolved_paths == [resolved]
        s3control_client.get_access_point.assert_called_with(
            AccountId="123456789012",
            Name=name
        )

    @pytest.mark.parametrize(
            "path,expected_has_underlying_s3_path",
            [(_BASE_ACCESSPOINT_ARN,True),
             (f"{_BASE_ACCESSPOINT_ARN}/mykey",True),
             (f"{_BASE_ACCESSPOINT_ARN}/myprefix/mykey",True),
             (_BASE_ACCESSPOINT_ALIAS,True),
             (_BASE_OUTPOST_ACCESSPOINT_ARN,True),
             (_BASE_OUTPOST_ACCESSPOINT_ALIAS,True),
             (_BASE_MRAP_ARN,True),
             ("s3://mybucket/",False),
             ("s3://mybucket/mykey",False),
             ("s3://mybucket/myprefix/mykey",False)]
    )
    def test_has_underlying_s3_path(self, path, expected_has_underlying_s3_path):
        has_underlying_s3_path = S3PathResolver.has_underlying_s3_path(path)
        assert has_underlying_s3_path == expected_has_underlying_s3_path

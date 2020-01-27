# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import datetime
import errno
import os
import shutil
import tempfile

from dateutil.tz import tzlocal
from s3transfer.futures import TransferMeta, TransferFuture
from s3transfer.manager import TransferConfig

from awscli.testutils import unittest, mock
from awscli.testutils import FileCreator
from awscli.compat import queue
from awscli.customizations.s3 import utils
from awscli.customizations.s3.fileinfo import FileInfo
from awscli.customizations.s3.subscribers import (
    ProvideSizeSubscriber, OnDoneFilteredSubscriber,
    ProvideUploadContentTypeSubscriber,
    ProvideLastModifiedTimeSubscriber, DirectoryCreatorSubscriber,
    DeleteSourceObjectSubscriber, DeleteSourceFileSubscriber,
    DeleteCopySourceObjectSubscriber, CreateDirectoryError,
    CopyPropsSubscriberFactory, ReplaceMetadataDirectiveSubscriber,
    ReplaceTaggingDirectiveSubscriber, SetMetadataDirectivePropsSubscriber,
    SetTagsSubscriber
)
from awscli.customizations.s3.results import WarningResult
from tests.unit.customizations.s3 import FakeTransferFuture
from tests.unit.customizations.s3 import FakeTransferFutureMeta
from tests.unit.customizations.s3 import FakeTransferFutureCallArgs


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
        _, utime = utils.get_file_stat(self.filename)
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

    def test_on_queued_failure_propogates_create_directory_error(self):
        # If makedirs() raises an OSError of exception, we should
        # propogate the exception with a better worded CreateDirectoryError.
        with mock.patch('os.makedirs') as makedirs_patch:
            makedirs_patch.side_effect = OSError()
            with self.assertRaises(CreateDirectoryError):
                self.subscriber.on_queued(self.future)
        self.assertFalse(os.path.exists(self.directory_to_create))

    def test_on_queued_failure_propogates_clear_error_message(self):
        # If makedirs() raises an OSError of exception, we should
        # propogate the exception.
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


class BaseCopyPropsSubscriberTest(unittest.TestCase):
    def setUp(self):
        self.client = mock.Mock()
        self.transfer_config = TransferConfig()
        self.cli_params = {}
        self.source_bucket = 'source-bucket'
        self.source_key = 'source-key'
        self.bucket = 'bucket'
        self.key = 'key'
        self.future = self.get_transfer_future()

    def get_transfer_future(self, size=0):
        return FakeTransferFuture(
            meta=FakeTransferFutureMeta(
                call_args=FakeTransferFutureCallArgs(
                    copy_source={
                        'Bucket': self.source_bucket,
                        'Key': self.source_key,
                    },
                    bucket=self.bucket,
                    key=self.key,
                    extra_args={}
                ),
                size=size,
                user_context={},
            )

        )

    def assert_extra_args(self, future, expected_extra_args):
        self.assertEqual(expected_extra_args, future.meta.call_args.extra_args)

    def set_size_for_mp_copy(self, future):
        future.meta.size = 10 * (1024 ** 2)

    def set_cli_params_to_recursive_copy(self):
        self.cli_params['dir_op'] = True


class TestCopyPropsSubscriberFactory(BaseCopyPropsSubscriberTest):
    def setUp(self):
        super(TestCopyPropsSubscriberFactory, self).setUp()
        self.set_cli_params_to_recursive_copy()
        self.factory = CopyPropsSubscriberFactory(
            self.client, self.transfer_config, self.cli_params
        )
        self.fileinfo = self.get_fileinfo()

    def set_copy_props(self, value):
        self.cli_params['copy_props'] = value

    def get_fileinfo(self, **override_kwargs):
        fileinfo_kwargs = {
            'src': 'src'
        }
        fileinfo_kwargs.update(override_kwargs)
        return FileInfo(**fileinfo_kwargs)

    def assert_subscriber_classes(self, actual_subscribers, expected_classes):
        self.assertEqual(len(actual_subscribers), len(expected_classes))
        for i, subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(subscriber, expected_classes[i])

    def test_get_subscribers_for_copy_props_none(self):
        self.set_copy_props('none')
        subscribers = self.factory.get_subscribers(self.fileinfo)
        self.assert_subscriber_classes(
            subscribers,
            [
                ReplaceMetadataDirectiveSubscriber,
                ReplaceTaggingDirectiveSubscriber,
            ]
        )

    def test_get_subscribers_for_copy_props_metadata_directive(self):
        self.set_copy_props('metadata-directive')
        subscribers = self.factory.get_subscribers(self.fileinfo)
        self.assert_subscriber_classes(
            subscribers,
            [
                SetMetadataDirectivePropsSubscriber,
                ReplaceTaggingDirectiveSubscriber,
            ]
        )

    def test_get_subscribers_for_copy_props_default(self):
        self.set_copy_props('default')
        subscribers = self.factory.get_subscribers(self.fileinfo)
        self.assert_subscriber_classes(
            subscribers,
            [
                SetMetadataDirectivePropsSubscriber,
                SetTagsSubscriber,
            ]
        )

    def test_get_subscribers_injects_cached_head_object_response(self):
        self.set_copy_props('default')
        self.cli_params['dir_op'] = False
        self.fileinfo.associated_response_data = {
            'ContentType': 'from-cache'
        }
        metadata_subscriber = self.factory.get_subscribers(self.fileinfo)[0]
        self.set_size_for_mp_copy(self.future)
        metadata_subscriber.on_queued(self.future)
        self.assertFalse(self.client.head_object.called)
        self.assert_extra_args(self.future, {'ContentType': 'from-cache'})


class TestReplaceMetadataDirectiveSubscriber(BaseCopyPropsSubscriberTest):
    def test_on_queued(self):
        ReplaceMetadataDirectiveSubscriber().on_queued(self.future)
        self.assert_extra_args(self.future, {'MetadataDirective': 'REPLACE'})


class TestReplaceTaggingDirectiveSubscriber(BaseCopyPropsSubscriberTest):
    def test_on_queued(self):
        ReplaceTaggingDirectiveSubscriber().on_queued(self.future)
        self.assert_extra_args(self.future, {'TaggingDirective': 'REPLACE'})


class TestSetMetadataDirectivePropsSubscriber(BaseCopyPropsSubscriberTest):
    def setUp(self):
        super(TestSetMetadataDirectivePropsSubscriber, self).setUp()
        self.head_object_response = {}
        self.subscriber = SetMetadataDirectivePropsSubscriber(
            client=self.client,
            transfer_config=self.transfer_config,
            cli_params=self.cli_params,
            head_object_response=self.head_object_response,
        )
        self.all_props = {
            'CacheControl': 'cache-control',
            'ContentDisposition': 'content-disposition',
            'ContentEncoding': 'content-encoding',
            'ContentLanguage': 'content-language',
            'ContentType': 'content-type',
            'Expires': 'Tue, 07 Jan 2020 20:40:03 GMT',
            'Metadata': {'key': 'value'}
        }

    def set_head_object_response_props(self, **props):
        self.head_object_response.update(props)

    def set_extra_args(self, future, **extra_args):
        future.meta.call_args.extra_args.update(**extra_args)

    def test_does_not_set_props_for_copy_object(self):
        self.subscriber.on_queued(self.future)
        self.assert_extra_args(self.future, {})

    def test_sets_props_for_mp_copy(self):
        self.set_head_object_response_props(**self.all_props)
        self.set_size_for_mp_copy(self.future)
        self.subscriber.on_queued(self.future)
        self.assert_extra_args(self.future, self.all_props)

    def test_filters_out_props_not_in_metadata_directive(self):
        self.set_head_object_response_props(DoNotInclude='do-not-include')
        self.set_size_for_mp_copy(self.future)
        self.subscriber.on_queued(self.future)
        self.assert_extra_args(self.future, {})

    def test_sets_props_for_cache_control_override(self):
        self.set_extra_args(self.future, CacheControl='override')
        self.subscriber.on_queued(self.future)
        self.assert_extra_args(
            self.future,
            {'MetadataDirective': 'REPLACE', 'CacheControl': 'override'}
        )

    def test_sets_props_for_content_disposition_override(self):
        self.set_extra_args(self.future, ContentDisposition='override')
        self.subscriber.on_queued(self.future)
        self.assert_extra_args(
            self.future,
            {'MetadataDirective': 'REPLACE', 'ContentDisposition': 'override'}
        )

    def test_sets_props_for_content_encoding_override(self):
        self.set_extra_args(self.future, ContentEncoding='override')
        self.subscriber.on_queued(self.future)
        self.assert_extra_args(
            self.future,
            {'MetadataDirective': 'REPLACE', 'ContentEncoding': 'override'}
        )

    def test_sets_props_for_content_language_override(self):
        self.set_extra_args(self.future, ContentLanguage='override')
        self.subscriber.on_queued(self.future)
        self.assert_extra_args(
            self.future,
            {'MetadataDirective': 'REPLACE', 'ContentLanguage': 'override'}
        )

    def test_sets_props_for_content_type_override(self):
        self.set_extra_args(self.future, ContentType='override')
        self.subscriber.on_queued(self.future)
        self.assert_extra_args(
            self.future,
            {'MetadataDirective': 'REPLACE', 'ContentType': 'override'}
        )

    def test_sets_props_for_expires_override(self):
        self.set_extra_args(self.future, Expires='override')
        self.subscriber.on_queued(self.future)
        self.assert_extra_args(
            self.future,
            {'MetadataDirective': 'REPLACE', 'Expires': 'override'}
        )

    def test_sets_props_for_metadata_override(self):
        self.set_extra_args(self.future, Metadata={'key': 'override'})
        self.subscriber.on_queued(self.future)
        self.assert_extra_args(
            self.future,
            {'MetadataDirective': 'REPLACE', 'Metadata': {'key': 'override'}}
        )

    def test_overrides_merges_with_head_object_data(self):
        self.set_head_object_response_props(**self.all_props)
        self.set_extra_args(
            self.future, ContentType='override', Metadata={'key': 'override'})
        self.subscriber.on_queued(self.future)
        expected_extra_args = {
            'CacheControl': 'cache-control',
            'ContentDisposition': 'content-disposition',
            'ContentEncoding': 'content-encoding',
            'ContentLanguage': 'content-language',
            'ContentType': 'override',
            'Expires': 'Tue, 07 Jan 2020 20:40:03 GMT',
            'Metadata': {'key': 'override'},
            'MetadataDirective': 'REPLACE'
        }
        self.assert_extra_args(self.future, expected_extra_args)

    def test_can_override_all_metadata_props(self):
        self.set_head_object_response_props(**self.all_props)
        all_override_args = {
            'CacheControl': 'override',
            'ContentDisposition': 'override',
            'ContentEncoding': 'override',
            'ContentLanguage': 'override',
            'ContentType': 'override',
            'Expires': 'override',
            'Metadata': {'key': 'override'}
        }
        self.set_extra_args(self.future, **all_override_args)
        self.subscriber.on_queued(self.future)
        expected_args = all_override_args.copy()
        expected_args['MetadataDirective'] = 'REPLACE'
        self.assert_extra_args(self.future, expected_args)

    def test_makes_head_object_call_if_not_cached(self):
        subscriber = SetMetadataDirectivePropsSubscriber(
            client=self.client,
            transfer_config=self.transfer_config,
            cli_params=self.cli_params,
            head_object_response=None,
        )
        self.client.head_object.return_value = {}
        self.set_size_for_mp_copy(self.future)
        subscriber.on_queued(self.future)
        self.client.head_object.assert_called_with(
            Bucket=self.source_bucket, Key=self.source_key)

    def test_add_extra_params_to_head_object_call(self):
        subscriber = SetMetadataDirectivePropsSubscriber(
            client=self.client,
            transfer_config=self.transfer_config,
            cli_params=self.cli_params,
            head_object_response=None,
        )
        self.client.head_object.return_value = {}
        self.cli_params['request_payer'] = 'requester'
        self.set_size_for_mp_copy(self.future)
        subscriber.on_queued(self.future)
        self.client.head_object.assert_called_with(
            Bucket=self.source_bucket, Key=self.source_key,
            RequestPayer='requester'
        )


class PutObjectTaggingException(Exception):
    pass


class TestSetTagsSubscriber(BaseCopyPropsSubscriberTest):
    def setUp(self):
        super(TestSetTagsSubscriber, self).setUp()
        self.subscriber = SetTagsSubscriber(
            client=self.client,
            transfer_config=self.transfer_config,
            cli_params=self.cli_params,
        )
        self.tagging_response = {
            'TagSet': [
                {
                    'Key': 'tag1',
                    'Value': 'val1'
                },
                {
                    'Key': 'tag2',
                    'Value': 'val2'
                },
            ]
        }
        self.url_encoded_tags = 'tag1=val1&tag2=val2'
        self.tagging_response_over_limit = {
            'TagSet': [
                {
                    'Key': 'tag',
                    'Value': 'val1' * (2 * 1024)
                },
            ]
        }

    def test_does_not_set_tags_for_copy_object(self):
        self.subscriber.on_queued(self.future)
        self.assert_extra_args(self.future, {})

    def test_sets_tags_for_mp_copy(self):
        self.set_size_for_mp_copy(self.future)
        self.client.get_object_tagging.return_value = self.tagging_response
        self.subscriber.on_queued(self.future)
        self.client.get_object_tagging.assert_called_with(
            Bucket=self.source_bucket, Key=self.source_key
        )
        self.assert_extra_args(self.future, {'Tagging': self.url_encoded_tags})

    def test_does_not_set_tags_if_not_present(self):
        self.set_size_for_mp_copy(self.future)
        self.client.get_object_tagging.return_value = {'TagSet': []}
        self.subscriber.on_queued(self.future)
        self.client.get_object_tagging.assert_called_with(
            Bucket=self.source_bucket, Key=self.source_key
        )
        self.assert_extra_args(self.future, {})

    def test_sets_tags_using_put_object_tagging_if_over_size_limit(self):
        self.set_size_for_mp_copy(self.future)
        self.client.get_object_tagging.return_value = \
            self.tagging_response_over_limit
        self.subscriber.on_queued(self.future)
        self.client.get_object_tagging.assert_called_with(
            Bucket=self.source_bucket, Key=self.source_key
        )
        self.assert_extra_args(self.future, {})
        self.subscriber.on_done(self.future)
        self.client.put_object_tagging.assert_called_with(
            Bucket=self.bucket, Key=self.key,
            Tagging=self.tagging_response_over_limit,
        )

    def test_does_not_call_put_object_tagging_if_transfer_fails(self):
        self.set_size_for_mp_copy(self.future)
        self.client.get_object_tagging.return_value = \
            self.tagging_response_over_limit
        self.subscriber.on_queued(self.future)
        self.future.set_exception(Exception())
        self.subscriber.on_done(self.future)
        self.assertFalse(self.client.put_object_tagging.called)

    def test_put_object_tagging_propagates_error_and_cleans_up_if_fails(self):
        self.set_size_for_mp_copy(self.future)
        self.client.get_object_tagging.return_value = \
            self.tagging_response_over_limit
        self.subscriber.on_queued(self.future)

        self.client.put_object_tagging.side_effect = \
            PutObjectTaggingException()
        self.subscriber.on_done(self.future)

        with self.assertRaises(PutObjectTaggingException):
            self.future.result()

        self.client.put_object_tagging.assert_called_with(
            Bucket=self.bucket, Key=self.key,
            Tagging=self.tagging_response_over_limit,
        )
        self.client.delete_object.assert_called_once_with(
            Bucket=self.bucket, Key=self.key,
        )

    def test_add_extra_params_to_delete_object_call(self):
        self.cli_params['request_payer'] = 'requester'
        self.set_size_for_mp_copy(self.future)
        self.client.get_object_tagging.return_value = \
            self.tagging_response_over_limit
        self.subscriber.on_queued(self.future)

        self.client.put_object_tagging.side_effect = \
            PutObjectTaggingException()
        self.subscriber.on_done(self.future)

        self.client.delete_object.assert_called_once_with(
            Bucket=self.bucket, Key=self.key, RequestPayer='requester'
        )

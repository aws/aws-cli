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
import os

import mock
from s3transfer.manager import TransferManager

from awscli.testutils import unittest
from awscli.testutils import FileCreator
from awscli.compat import queue
from awscli.customizations.s3.s3handler import S3TransferHandler
from awscli.customizations.s3.s3handler import S3TransferHandlerFactory
from awscli.customizations.s3.s3handler import UploadRequestSubmitter
from awscli.customizations.s3.s3handler import DownloadRequestSubmitter
from awscli.customizations.s3.s3handler import CopyRequestSubmitter
from awscli.customizations.s3.s3handler import UploadStreamRequestSubmitter
from awscli.customizations.s3.s3handler import DownloadStreamRequestSubmitter
from awscli.customizations.s3.s3handler import DeleteRequestSubmitter
from awscli.customizations.s3.s3handler import LocalDeleteRequestSubmitter
from awscli.customizations.s3.fileinfo import FileInfo
from awscli.customizations.s3.results import QueuedResult
from awscli.customizations.s3.results import SuccessResult
from awscli.customizations.s3.results import FailureResult
from awscli.customizations.s3.results import QueuedResultSubscriber
from awscli.customizations.s3.results import ProgressResultSubscriber
from awscli.customizations.s3.results import DoneResultSubscriber
from awscli.customizations.s3.results import ResultRecorder
from awscli.customizations.s3.results import ResultProcessor
from awscli.customizations.s3.results import CommandResultRecorder
from awscli.customizations.s3.results import DryRunResult
from awscli.customizations.s3.utils import MAX_UPLOAD_SIZE
from awscli.customizations.s3.utils import NonSeekableStream
from awscli.customizations.s3.utils import StdoutBytesWriter
from awscli.customizations.s3.utils import WarningResult
from awscli.customizations.s3.subscribers import (
    ProvideSizeSubscriber, SetMetadataDirectivePropsSubscriber,
    SetTagsSubscriber, ProvideUploadContentTypeSubscriber,
    ProvideLastModifiedTimeSubscriber,
    DirectoryCreatorSubscriber, DeleteSourceFileSubscriber,
    DeleteSourceObjectSubscriber,

)
from awscli.customizations.s3.transferconfig import RuntimeConfig


def runtime_config(**kwargs):
    return RuntimeConfig().build_config(**kwargs)


class TestS3TransferHandlerFactory(unittest.TestCase):
    def setUp(self):
        self.cli_params = {}
        self.runtime_config = runtime_config()
        self.client = mock.Mock()
        self.result_queue = queue.Queue()

    def test_call(self):
        factory = S3TransferHandlerFactory(
            self.cli_params, self.runtime_config)
        self.assertIsInstance(
            factory(self.client, self.result_queue), S3TransferHandler)


class TestS3TransferHandler(unittest.TestCase):
    def setUp(self):
        self.result_queue = queue.Queue()
        self.result_recorder = ResultRecorder()
        self.processed_results = []
        self.result_processor = ResultProcessor(
            self.result_queue,
            [self.result_recorder, self.processed_results.append]
        )
        self.command_result_recorder = CommandResultRecorder(
            self.result_queue, self.result_recorder, self.result_processor)

        self.transfer_manager = mock.Mock(spec=TransferManager)
        self.transfer_manager.__enter__ = mock.Mock()
        self.transfer_manager.__exit__ = mock.Mock()
        self.parameters = {}
        self.s3_transfer_handler = S3TransferHandler(
            self.transfer_manager, self.parameters,
            self.command_result_recorder
        )

    def test_call_return_command_result(self):
        num_failures = 5
        num_warnings = 3
        self.result_recorder.files_failed = num_failures
        self.result_recorder.files_warned = num_warnings
        command_result = self.s3_transfer_handler.call([])
        self.assertEqual(command_result, (num_failures, num_warnings))

    def test_enqueue_uploads(self):
        fileinfos = []
        num_transfers = 5
        for _ in range(num_transfers):
            fileinfos.append(
                FileInfo(src='filename', dest='bucket/key',
                         operation_name='upload'))

        self.s3_transfer_handler.call(fileinfos)
        self.assertEqual(
            self.transfer_manager.upload.call_count, num_transfers)

    def test_enqueue_downloads(self):
        fileinfos = []
        num_transfers = 5
        for _ in range(num_transfers):
            fileinfos.append(
                FileInfo(src='bucket/key', dest='filename',
                         compare_key='key',
                         operation_name='download'))

        self.s3_transfer_handler.call(fileinfos)
        self.assertEqual(
            self.transfer_manager.download.call_count, num_transfers)

    def test_enqueue_copies(self):
        fileinfos = []
        num_transfers = 5
        for _ in range(num_transfers):
            fileinfos.append(
                FileInfo(src='sourcebucket/sourcekey', dest='bucket/key',
                         compare_key='key',
                         operation_name='copy'))

        self.s3_transfer_handler.call(fileinfos)
        self.assertEqual(
            self.transfer_manager.copy.call_count, num_transfers)

    def test_exception_when_enqueuing(self):
        fileinfos = [
            FileInfo(src='filename', dest='bucket/key',
                     operation_name='upload')
        ]
        self.transfer_manager.__exit__.side_effect = Exception(
            'some exception')
        command_result = self.s3_transfer_handler.call(fileinfos)
        # Exception should have been raised casing the command result to
        # have failed results of one.
        self.assertEqual(command_result, (1, 0))

    def test_enqueue_upload_stream(self):
        self.parameters['is_stream'] = True
        self.s3_transfer_handler.call(
            [FileInfo(src='-', dest='bucket/key', operation_name='upload')])
        self.assertEqual(
            self.transfer_manager.upload.call_count, 1)
        upload_call_kwargs = self.transfer_manager.upload.call_args[1]
        self.assertIsInstance(
            upload_call_kwargs['fileobj'], NonSeekableStream)

    def test_enqueue_dowload_stream(self):
        self.parameters['is_stream'] = True
        self.s3_transfer_handler.call(
            [FileInfo(src='bucket/key', dest='-',
                      compare_key='key',
                      operation_name='download')])
        self.assertEqual(
            self.transfer_manager.download.call_count, 1)
        download_call_kwargs = self.transfer_manager.download.call_args[1]
        self.assertIsInstance(
            download_call_kwargs['fileobj'], StdoutBytesWriter)

    def test_enqueue_deletes(self):
        fileinfos = []
        num_transfers = 5
        for _ in range(num_transfers):
            fileinfos.append(
                FileInfo(src='bucket/key', dest=None, operation_name='delete',
                         src_type='s3'))

        self.s3_transfer_handler.call(fileinfos)
        self.assertEqual(
            self.transfer_manager.delete.call_count, num_transfers)

    def test_enqueue_local_deletes(self):
        fileinfos = []
        num_transfers = 5
        for _ in range(num_transfers):
            fileinfos.append(
                FileInfo(src='myfile', dest=None, operation_name='delete',
                         src_type='local'))

        self.s3_transfer_handler.call(fileinfos)
        # The number of processed results will be equal to:
        # number_of_local_deletes * 2 + 1
        # The 2 represents the QueuedResult and SuccessResult/FailureResult
        # for each transfer
        # The 1 represents the TotalFinalSubmissionResult
        self.assertEqual(len(self.processed_results), 11)

        # Make sure that the results are as expected by checking just one
        # of them
        first_submitted_result = self.processed_results[0]
        self.assertEqual(first_submitted_result.transfer_type, 'delete')
        self.assertTrue(first_submitted_result.src.endswith('myfile'))

        # Also make sure that transfer manager's delete() was never called
        self.assertEqual(self.transfer_manager.delete.call_count, 0)

    def test_notifies_total_submissions(self):
        fileinfos = []
        num_transfers = 5
        for _ in range(num_transfers):
            fileinfos.append(
                FileInfo(src='bucket/key', dest='filename',
                         compare_key='key',
                         operation_name='download'))

        self.s3_transfer_handler.call(fileinfos)
        self.assertEqual(
            self.result_recorder.final_expected_files_transferred,
            num_transfers
        )

    def test_notifies_total_submissions_accounts_for_skips(self):
        fileinfos = []
        num_transfers = 5
        for _ in range(num_transfers):
            fileinfos.append(
                FileInfo(src='bucket/key', dest='filename',
                         compare_key='key',
                         operation_name='download'))

        # Add a fileinfo that should get skipped. To skip, we do a glacier
        # download.
        fileinfos.append(FileInfo(
            src='bucket/key', dest='filename', operation_name='download',
            compare_key='key',
            associated_response_data={'StorageClass': 'GLACIER'}))
        self.s3_transfer_handler.call(fileinfos)
        # Since the last glacier download was skipped the final expected
        # total should be equal to the number of transfers provided in the
        # for loop.
        self.assertEqual(
            self.result_recorder.final_expected_files_transferred,
            num_transfers
        )


class BaseTransferRequestSubmitterTest(unittest.TestCase):
    def setUp(self):
        self.transfer_manager = mock.Mock(spec=TransferManager)
        self.result_queue = queue.Queue()
        self.cli_params = {}
        self.filename = 'myfile'
        self.bucket = 'mybucket'
        self.key = 'mykey'


class TestUploadRequestSubmitter(BaseTransferRequestSubmitterTest):
    def setUp(self):
        super(TestUploadRequestSubmitter, self).setUp()
        self.transfer_request_submitter = UploadRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key,
            operation_name='upload')
        self.assertTrue(
            self.transfer_request_submitter.can_submit(fileinfo))
        fileinfo.operation_name = 'foo'
        self.assertFalse(
            self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key)
        self.cli_params['guess_mime_type'] = True  # Default settings
        future = self.transfer_request_submitter.submit(fileinfo)

        self.assertIs(self.transfer_manager.upload.return_value, future)
        upload_call_kwargs = self.transfer_manager.upload.call_args[1]
        self.assertEqual(upload_call_kwargs['fileobj'], self.filename)
        self.assertEqual(upload_call_kwargs['bucket'], self.bucket)
        self.assertEqual(upload_call_kwargs['key'], self.key)
        self.assertEqual(upload_call_kwargs['extra_args'], {})

        # Make sure the subscriber applied are of the correct type and order
        ref_subscribers = [
            ProvideSizeSubscriber,
            QueuedResultSubscriber,
            ProvideUploadContentTypeSubscriber,
            ProgressResultSubscriber,
            DoneResultSubscriber,
        ]
        actual_subscribers = upload_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_submit_with_extra_args(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key)
        # Set some extra argument like storage_class to make sure cli
        # params get mapped to request parameters.
        self.cli_params['storage_class'] = 'STANDARD_IA'
        self.transfer_request_submitter.submit(fileinfo)

        upload_call_kwargs = self.transfer_manager.upload.call_args[1]
        self.assertEqual(
            upload_call_kwargs['extra_args'], {'StorageClass': 'STANDARD_IA'})

    def test_submit_when_content_type_specified(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key)
        self.cli_params['content_type'] = 'text/plain'
        self.transfer_request_submitter.submit(fileinfo)

        upload_call_kwargs = self.transfer_manager.upload.call_args[1]
        self.assertEqual(
            upload_call_kwargs['extra_args'], {'ContentType': 'text/plain'})
        ref_subscribers = [
            ProvideSizeSubscriber,
            QueuedResultSubscriber,
            ProgressResultSubscriber,
            DoneResultSubscriber,
        ]
        actual_subscribers = upload_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_submit_when_no_guess_content_mime_type(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key)
        self.cli_params['guess_mime_type'] = False
        self.transfer_request_submitter.submit(fileinfo)

        upload_call_kwargs = self.transfer_manager.upload.call_args[1]
        ref_subscribers = [
            ProvideSizeSubscriber,
            QueuedResultSubscriber,
            ProgressResultSubscriber,
            DoneResultSubscriber,
        ]
        actual_subscribers = upload_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_warn_on_too_large_transfer(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key,
            size=MAX_UPLOAD_SIZE+1)
        future = self.transfer_request_submitter.submit(fileinfo)

        # A warning should have been submitted because it is too large.
        warning_result = self.result_queue.get()
        self.assertIsInstance(warning_result, WarningResult)
        self.assertIn('exceeds s3 upload limit', warning_result.message)

        # Make sure that the transfer was still attempted
        self.assertIs(self.transfer_manager.upload.return_value, future)
        self.assertEqual(len(self.transfer_manager.upload.call_args_list), 1)

    def test_dry_run(self):
        self.cli_params['dryrun'] = True
        self.transfer_request_submitter = UploadRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)
        fileinfo = FileInfo(
            src=self.filename, src_type='local', operation_name='upload',
            dest=self.bucket + '/' + self.key, dest_type='s3')
        self.transfer_request_submitter.submit(fileinfo)

        result = self.result_queue.get()
        self.assertIsInstance(result, DryRunResult)
        self.assertEqual(result.transfer_type, 'upload')
        self.assertTrue(result.src.endswith(self.filename))
        self.assertEqual(result.dest, 's3://' + self.bucket + '/' + self.key)

    def test_submit_move_adds_delete_source_subscriber(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key)
        self.cli_params['guess_mime_type'] = True  # Default settings
        self.cli_params['is_move'] = True
        self.transfer_request_submitter.submit(fileinfo)
        ref_subscribers = [
            ProvideSizeSubscriber,
            QueuedResultSubscriber,
            ProvideUploadContentTypeSubscriber,
            DeleteSourceFileSubscriber,
            ProgressResultSubscriber,
            DoneResultSubscriber,
        ]
        upload_call_kwargs = self.transfer_manager.upload.call_args[1]
        actual_subscribers = upload_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])


class TestDownloadRequestSubmitter(BaseTransferRequestSubmitterTest):
    def setUp(self):
        super(TestDownloadRequestSubmitter, self).setUp()
        self.transfer_request_submitter = DownloadRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)

    def assert_no_downloads_happened(self):
        self.assertEqual(len(self.transfer_manager.download.call_args_list), 0)

    def create_file_info(self, key, associated_response_data=None):
        kwargs = {
            'src': self.bucket + '/' + key,
            'src_type': 's3',
            'dest': self.filename,
            'dest_type': 'local',
            'operation_name': 'download',
            'compare_key': key,
        }
        if associated_response_data is not None:
            kwargs['associated_response_data'] = associated_response_data
        return FileInfo(**kwargs)

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=self.filename,
            operation_name='download')
        self.assertTrue(
            self.transfer_request_submitter.can_submit(fileinfo))
        fileinfo.operation_name = 'foo'
        self.assertFalse(
            self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        fileinfo = self.create_file_info(self.key)
        future = self.transfer_request_submitter.submit(fileinfo)

        self.assertIs(self.transfer_manager.download.return_value, future)
        download_call_kwargs = self.transfer_manager.download.call_args[1]
        self.assertEqual(download_call_kwargs['fileobj'], self.filename)
        self.assertEqual(download_call_kwargs['bucket'], self.bucket)
        self.assertEqual(download_call_kwargs['key'], self.key)
        self.assertEqual(download_call_kwargs['extra_args'], {})

        # Make sure the subscriber applied are of the correct type and order
        ref_subscribers = [
            ProvideSizeSubscriber,
            QueuedResultSubscriber,
            DirectoryCreatorSubscriber,
            ProvideLastModifiedTimeSubscriber,
            ProgressResultSubscriber,
            DoneResultSubscriber,
        ]
        actual_subscribers = download_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_submit_with_extra_args(self):
        fileinfo = self.create_file_info(self.key)
        self.cli_params['sse_c'] = 'AES256'
        self.cli_params['sse_c_key'] = 'mykey'
        self.transfer_request_submitter.submit(fileinfo)

        # Set some extra argument like sse_c to make sure cli
        # params get mapped to request parameters.
        download_call_kwargs = self.transfer_manager.download.call_args[1]
        self.assertEqual(
            download_call_kwargs['extra_args'],
            {'SSECustomerAlgorithm': 'AES256', 'SSECustomerKey': 'mykey'}
        )

    def test_warn_glacier_for_incompatible(self):
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=self.filename,
            operation_name='download',
            associated_response_data={
                'StorageClass': 'GLACIER',
            }
        )
        future = self.transfer_request_submitter.submit(fileinfo)

        # A warning should have been submitted because it is a non-restored
        # glacier object.
        warning_result = self.result_queue.get()
        self.assertIsInstance(warning_result, WarningResult)
        self.assertIn(
            'Unable to perform download operations on GLACIER objects',
            warning_result.message)

        # The transfer should have been skipped.
        self.assertIsNone(future)
        self.assert_no_downloads_happened()

    def test_not_warn_glacier_for_compatible(self):
        fileinfo = self.create_file_info(
            self.key, associated_response_data={
                'StorageClass': 'GLACIER',
                'Restore': 'ongoing-request="false"'
            }
        )
        future = self.transfer_request_submitter.submit(fileinfo)

        # A warning should have not been submitted because it is a restored
        # glacier object.
        self.assertTrue(self.result_queue.empty())

        # And the transfer should not have been skipped.
        self.assertIs(self.transfer_manager.download.return_value, future)
        self.assertEqual(len(self.transfer_manager.download.call_args_list), 1)

    def test_warn_glacier_force_glacier(self):
        self.cli_params['force_glacier_transfer'] = True
        fileinfo = self.create_file_info(
            self.key,
            associated_response_data={
                'StorageClass': 'GLACIER',
            }
        )
        future = self.transfer_request_submitter.submit(fileinfo)

        # A warning should have not been submitted because it is glacier
        # transfers were forced.
        self.assertTrue(self.result_queue.empty())
        self.assertIs(self.transfer_manager.download.return_value, future)
        self.assertEqual(len(self.transfer_manager.download.call_args_list), 1)

    def test_warn_glacier_ignore_glacier_warnings(self):
        self.cli_params['ignore_glacier_warnings'] = True
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=self.filename,
            operation_name='download',
            associated_response_data={
                'StorageClass': 'GLACIER',
            }
        )
        future = self.transfer_request_submitter.submit(fileinfo)

        # A warning should have not been submitted because it was specified
        # to ignore glacier warnings.
        self.assertTrue(self.result_queue.empty())
        # But the transfer still should have been skipped.
        self.assertIsNone(future)
        self.assert_no_downloads_happened()

    def test_warn_and_ignore_on_parent_dir_reference(self):
        fileinfo = self.create_file_info('../foo.txt')
        future = self.transfer_request_submitter.submit(fileinfo)
        warning_result = self.result_queue.get()
        self.assertIsInstance(warning_result, WarningResult)
        self.assert_no_downloads_happened()

    def test_warn_and_ignore_with_leading_chars(self):
        fileinfo = self.create_file_info('a/../../foo.txt')
        future = self.transfer_request_submitter.submit(fileinfo)
        warning_result = self.result_queue.get()
        self.assertIsInstance(warning_result, WarningResult)
        self.assert_no_downloads_happened()

    def test_allow_double_dots_that_dont_escape_cwd(self):
        self.cli_params['dryrun'] = True
        # This is fine because it's 'foo.txt'.
        fileinfo = self.create_file_info('a/../foo.txt')
        future = self.transfer_request_submitter.submit(fileinfo)
        self.assertIsInstance(self.result_queue.get(), DryRunResult)

    def test_dry_run(self):
        self.cli_params['dryrun'] = True
        self.transfer_request_submitter = DownloadRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)
        fileinfo = self.create_file_info(self.key)
        self.transfer_request_submitter.submit(fileinfo)

        result = self.result_queue.get()
        self.assertIsInstance(result, DryRunResult)
        self.assertEqual(result.transfer_type, 'download')
        self.assertTrue(result.dest.endswith(self.filename))
        self.assertEqual(result.src, 's3://' + self.bucket + '/' + self.key)

    def test_submit_move_adds_delete_source_subscriber(self):
        fileinfo = self.create_file_info(self.key)
        self.cli_params['guess_mime_type'] = True  # Default settings
        self.cli_params['is_move'] = True
        self.transfer_request_submitter.submit(fileinfo)
        ref_subscribers = [
            ProvideSizeSubscriber,
            QueuedResultSubscriber,
            DirectoryCreatorSubscriber,
            ProvideLastModifiedTimeSubscriber,
            DeleteSourceObjectSubscriber,
            ProgressResultSubscriber,
            DoneResultSubscriber,
        ]
        download_call_kwargs = self.transfer_manager.download.call_args[1]
        actual_subscribers = download_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])


class TestCopyRequestSubmitter(BaseTransferRequestSubmitterTest):
    def setUp(self):
        super(TestCopyRequestSubmitter, self).setUp()
        self.source_bucket = 'mysourcebucket'
        self.source_key = 'mysourcekey'
        self.transfer_request_submitter = CopyRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.source_bucket+'/'+self.source_key,
            dest=self.bucket+'/'+self.key, operation_name='copy')
        self.assertTrue(
            self.transfer_request_submitter.can_submit(fileinfo))
        fileinfo.operation_name = 'foo'
        self.assertFalse(
            self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        fileinfo = FileInfo(
            src=self.source_bucket+'/'+self.source_key,
            dest=self.bucket+'/'+self.key)
        self.cli_params['guess_mime_type'] = True  # Default settings
        future = self.transfer_request_submitter.submit(fileinfo)
        self.assertIs(self.transfer_manager.copy.return_value, future)
        copy_call_kwargs = self.transfer_manager.copy.call_args[1]
        self.assertEqual(
            copy_call_kwargs['copy_source'],
            {'Bucket': self.source_bucket, 'Key': self.source_key})
        self.assertEqual(copy_call_kwargs['bucket'], self.bucket)
        self.assertEqual(copy_call_kwargs['key'], self.key)
        self.assertEqual(copy_call_kwargs['extra_args'], {})

        # Make sure the subscriber applied are of the correct type and order
        ref_subscribers = [
            ProvideSizeSubscriber,
            QueuedResultSubscriber,
            SetMetadataDirectivePropsSubscriber,
            SetTagsSubscriber,
            ProgressResultSubscriber,
            DoneResultSubscriber,
        ]
        actual_subscribers = copy_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_submit_with_extra_args(self):
        fileinfo = FileInfo(
            src=self.source_bucket+'/'+self.source_key,
            dest=self.bucket+'/'+self.key)
        # Set some extra argument like storage_class to make sure cli
        # params get mapped to request parameters.
        self.cli_params['storage_class'] = 'STANDARD_IA'
        self.transfer_request_submitter.submit(fileinfo)

        copy_call_kwargs = self.transfer_manager.copy.call_args[1]
        self.assertEqual(
            copy_call_kwargs['extra_args'], {'StorageClass': 'STANDARD_IA'})

    def test_submit_when_content_type_specified(self):
        fileinfo = FileInfo(
            src=self.source_bucket+'/'+self.source_key,
            dest=self.bucket+'/'+self.key)
        self.cli_params['content_type'] = 'text/plain'
        self.transfer_request_submitter.submit(fileinfo)

        copy_call_kwargs = self.transfer_manager.copy.call_args[1]
        self.assertEqual(
            copy_call_kwargs['extra_args'], {'ContentType': 'text/plain'})
        ref_subscribers = [
            ProvideSizeSubscriber,
            QueuedResultSubscriber,
            SetMetadataDirectivePropsSubscriber,
            SetTagsSubscriber,
            ProgressResultSubscriber,
            DoneResultSubscriber,
        ]
        actual_subscribers = copy_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_metadata_directive_excludes_copy_props_subscribers(self):
        fileinfo = FileInfo(
            src=self.source_bucket+'/'+self.source_key,
            dest=self.bucket+'/'+self.key)
        self.cli_params['copy_props'] = 'default'
        self.cli_params['metadata_directive'] = 'REPLACE'
        self.transfer_request_submitter.submit(fileinfo)

        copy_call_kwargs = self.transfer_manager.copy.call_args[1]
        ref_subscribers = [
            ProvideSizeSubscriber,
            QueuedResultSubscriber,
            ProgressResultSubscriber,
            DoneResultSubscriber,
        ]
        actual_subscribers = copy_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_warn_glacier_for_incompatible(self):
        fileinfo = FileInfo(
            src=self.source_bucket+'/'+self.source_key,
            dest=self.bucket+'/'+self.key,
            operation_name='copy',
            associated_response_data={
                'StorageClass': 'GLACIER',
            }
        )
        future = self.transfer_request_submitter.submit(fileinfo)

        # A warning should have been submitted because it is a non-restored
        # glacier object.
        warning_result = self.result_queue.get()
        self.assertIsInstance(warning_result, WarningResult)
        self.assertIn(
            'Unable to perform copy operations on GLACIER objects',
            warning_result.message)

        # The transfer request should have never been sent therefore return
        # no future.
        self.assertIsNone(future)
        # The transfer should have been skipped.
        self.assertEqual(len(self.transfer_manager.copy.call_args_list), 0)

    def test_not_warn_glacier_for_compatible(self):
        fileinfo = FileInfo(
            src=self.source_bucket+'/'+self.source_key,
            dest=self.bucket+'/'+self.key,
            operation_name='copy',
            associated_response_data={
                'StorageClass': 'GLACIER',
                'Restore': 'ongoing-request="false"'
            }
        )
        future = self.transfer_request_submitter.submit(fileinfo)
        self.assertIs(self.transfer_manager.copy.return_value, future)

        # A warning should have not been submitted because it is a restored
        # glacier object.
        self.assertTrue(self.result_queue.empty())

        # And the transfer should not have been skipped.
        self.assertEqual(len(self.transfer_manager.copy.call_args_list), 1)

    def test_warn_glacier_force_glacier(self):
        self.cli_params['force_glacier_transfer'] = True
        fileinfo = FileInfo(
            src=self.source_bucket+'/'+self.source_key,
            dest=self.bucket+'/'+self.key,
            operation_name='copy',
            associated_response_data={
                'StorageClass': 'GLACIER',
            }
        )
        future = self.transfer_request_submitter.submit(fileinfo)
        self.assertIs(self.transfer_manager.copy.return_value, future)

        # A warning should have not been submitted because it is glacier
        # transfers were forced.
        self.assertTrue(self.result_queue.empty())
        self.assertEqual(len(self.transfer_manager.copy.call_args_list), 1)

    def test_warn_glacier_ignore_glacier_warnings(self):
        self.cli_params['ignore_glacier_warnings'] = True
        fileinfo = FileInfo(
            src=self.source_bucket+'/'+self.source_key,
            dest=self.bucket+'/'+self.key,
            operation_name='copy',
            associated_response_data={
                'StorageClass': 'GLACIER',
            }
        )
        future = self.transfer_request_submitter.submit(fileinfo)

        # The transfer request should have never been sent therefore return
        # no future.
        self.assertIsNone(future)
        # A warning should have not been submitted because it was specified
        # to ignore glacier warnings.
        self.assertTrue(self.result_queue.empty())
        # But the transfer still should have been skipped.
        self.assertEqual(len(self.transfer_manager.copy.call_args_list), 0)

    def test_dry_run(self):
        self.cli_params['dryrun'] = True
        self.transfer_request_submitter = CopyRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)
        fileinfo = FileInfo(
            src=self.source_bucket + '/' + self.source_key, src_type='s3',
            dest=self.bucket + '/' + self.key, dest_type='s3',
            operation_name='copy')
        self.transfer_request_submitter.submit(fileinfo)

        result = self.result_queue.get()
        self.assertIsInstance(result, DryRunResult)
        self.assertEqual(result.transfer_type, 'copy')
        source = 's3://' + self.source_bucket + '/' + self.source_key
        self.assertEqual(result.src, source)
        self.assertEqual(result.dest, 's3://' + self.bucket + '/' + self.key)

    def test_submit_move_adds_delete_source_subscriber(self):
        fileinfo = FileInfo(
            dest=self.source_bucket + '/' + self.source_key,
            src=self.bucket + '/' + self.key)
        self.cli_params['guess_mime_type'] = True  # Default settings
        self.cli_params['is_move'] = True
        self.transfer_request_submitter.submit(fileinfo)
        ref_subscribers = [
            ProvideSizeSubscriber,
            QueuedResultSubscriber,
            SetMetadataDirectivePropsSubscriber,
            SetTagsSubscriber,
            DeleteSourceObjectSubscriber,
            ProgressResultSubscriber,
            DoneResultSubscriber,
        ]
        copy_call_kwargs = self.transfer_manager.copy.call_args[1]
        actual_subscribers = copy_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])


class TestUploadStreamRequestSubmitter(BaseTransferRequestSubmitterTest):
    def setUp(self):
        super(TestUploadStreamRequestSubmitter, self).setUp()
        self.filename = '-'
        self.cli_params['is_stream'] = True
        self.transfer_request_submitter = UploadStreamRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key,
            operation_name='upload')
        self.assertTrue(
            self.transfer_request_submitter.can_submit(fileinfo))
        self.cli_params['is_stream'] = False
        self.assertFalse(
            self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key)
        future = self.transfer_request_submitter.submit(fileinfo)
        self.assertIs(self.transfer_manager.upload.return_value, future)

        upload_call_kwargs = self.transfer_manager.upload.call_args[1]
        self.assertIsInstance(
            upload_call_kwargs['fileobj'], NonSeekableStream)
        self.assertEqual(upload_call_kwargs['bucket'], self.bucket)
        self.assertEqual(upload_call_kwargs['key'], self.key)
        self.assertEqual(upload_call_kwargs['extra_args'], {})

        ref_subscribers = [
            QueuedResultSubscriber,
            ProgressResultSubscriber,
            DoneResultSubscriber,
        ]
        actual_subscribers = upload_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_submit_with_expected_size_provided(self):
        provided_size = 100
        self.cli_params['expected_size'] = provided_size
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key)
        self.transfer_request_submitter.submit(fileinfo)
        upload_call_kwargs = self.transfer_manager.upload.call_args[1]

        ref_subscribers = [
            ProvideSizeSubscriber,
            QueuedResultSubscriber,
            ProgressResultSubscriber,
            DoneResultSubscriber,
        ]
        actual_subscribers = upload_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])
        # The ProvideSizeSubscriber should be providing the correct size
        self.assertEqual(actual_subscribers[0].size, provided_size)

    def test_dry_run(self):
        self.cli_params['dryrun'] = True
        self.transfer_request_submitter = UploadStreamRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)
        fileinfo = FileInfo(
            src=self.filename, src_type='local', operation_name='upload',
            dest=self.bucket + '/' + self.key, dest_type='s3')
        self.transfer_request_submitter.submit(fileinfo)

        result = self.result_queue.get()
        self.assertIsInstance(result, DryRunResult)
        self.assertEqual(result.transfer_type, 'upload')
        self.assertEqual(result.dest, 's3://' + self.bucket + '/' + self.key)
        self.assertEqual(result.src, '-')


class TestDownloadStreamRequestSubmitter(BaseTransferRequestSubmitterTest):
    def setUp(self):
        super(TestDownloadStreamRequestSubmitter, self).setUp()
        self.filename = '-'
        self.cli_params['is_stream'] = True
        self.transfer_request_submitter = DownloadStreamRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=self.filename,
            operation_name='download')
        self.assertTrue(
            self.transfer_request_submitter.can_submit(fileinfo))
        self.cli_params['is_stream'] = False
        self.assertFalse(
            self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=self.filename,
            compare_key=self.key)
        future = self.transfer_request_submitter.submit(fileinfo)
        self.assertIs(self.transfer_manager.download.return_value, future)

        download_call_kwargs = self.transfer_manager.download.call_args[1]
        self.assertIsInstance(
            download_call_kwargs['fileobj'], StdoutBytesWriter)
        self.assertEqual(download_call_kwargs['bucket'], self.bucket)
        self.assertEqual(download_call_kwargs['key'], self.key)
        self.assertEqual(download_call_kwargs['extra_args'], {})

        ref_subscribers = [
            QueuedResultSubscriber,
            ProgressResultSubscriber,
            DoneResultSubscriber,
        ]
        actual_subscribers = download_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_dry_run(self):
        self.cli_params['dryrun'] = True
        self.transfer_request_submitter = DownloadStreamRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)
        fileinfo = FileInfo(
            dest=self.filename, dest_type='local', operation_name='download',
            src=self.bucket + '/' + self.key, src_type='s3',
            compare_key=self.key)
        self.transfer_request_submitter.submit(fileinfo)

        result = self.result_queue.get()
        self.assertIsInstance(result, DryRunResult)
        self.assertEqual(result.transfer_type, 'download')
        self.assertEqual(result.src, 's3://' + self.bucket + '/' + self.key)
        self.assertEqual(result.dest, '-')


class TestDeleteRequestSubmitter(BaseTransferRequestSubmitterTest):
    def setUp(self):
        super(TestDeleteRequestSubmitter, self).setUp()
        self.transfer_request_submitter = DeleteRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=None, operation_name='delete',
            src_type='s3')
        self.assertTrue(
            self.transfer_request_submitter.can_submit(fileinfo))
        fileinfo.operation_name = 'foo'
        self.assertFalse(
            self.transfer_request_submitter.can_submit(fileinfo))

    def test_cannot_submit_local_deletes(self):
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=None, operation_name='delete',
            src_type='local')
        self.assertFalse(
            self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=None, operation_name='delete')
        future = self.transfer_request_submitter.submit(fileinfo)
        self.assertIs(self.transfer_manager.delete.return_value, future)

        delete_call_kwargs = self.transfer_manager.delete.call_args[1]
        self.assertEqual(delete_call_kwargs['bucket'], self.bucket)
        self.assertEqual(delete_call_kwargs['key'], self.key)
        self.assertEqual(delete_call_kwargs['extra_args'], {})

        ref_subscribers = [
            QueuedResultSubscriber,
            ProgressResultSubscriber,
            DoneResultSubscriber,
        ]
        actual_subscribers = delete_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_dry_run(self):
        self.cli_params['dryrun'] = True
        self.transfer_request_submitter = DeleteRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)
        fileinfo = FileInfo(
            src=self.bucket + '/' + self.key, src_type='s3',
            dest=self.bucket + '/' + self.key, dest_type='s3',
            operation_name='delete')
        self.transfer_request_submitter.submit(fileinfo)

        result = self.result_queue.get()
        self.assertIsInstance(result, DryRunResult)
        self.assertEqual(result.transfer_type, 'delete')
        self.assertEqual(result.src, 's3://' + self.bucket + '/' + self.key)
        self.assertIsNone(result.dest)


class TestLocalDeleteRequestSubmitter(BaseTransferRequestSubmitterTest):
    def setUp(self):
        super(TestLocalDeleteRequestSubmitter, self).setUp()
        self.transfer_request_submitter = LocalDeleteRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)
        self.file_creator = FileCreator()

    def tearDown(self):
        super(TestLocalDeleteRequestSubmitter, self).tearDown()
        self.file_creator.remove_all()

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.filename, dest=None, operation_name='delete',
            src_type='local')
        self.assertTrue(
            self.transfer_request_submitter.can_submit(fileinfo))
        fileinfo.operation_name = 'foo'
        self.assertFalse(
            self.transfer_request_submitter.can_submit(fileinfo))

    def test_cannot_submit_remote_deletes(self):
        fileinfo = FileInfo(
            src=self.filename, dest=None, operation_name='delete',
            src_type='s3')
        self.assertFalse(
            self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        full_filename = self.file_creator.create_file(self.filename, 'content')
        fileinfo = FileInfo(
            src=full_filename, dest=None, operation_name='delete',
            src_type='local')
        rval = self.transfer_request_submitter.submit(fileinfo)
        self.assertTrue(rval)

        queued_result = self.result_queue.get()
        self.assertIsInstance(queued_result, QueuedResult)
        self.assertEqual(queued_result.transfer_type, 'delete')
        self.assertTrue(queued_result.src.endswith(self.filename))
        self.assertIsNone(queued_result.dest)
        self.assertEqual(queued_result.total_transfer_size, 0)

        failure_result = self.result_queue.get()
        self.assertIsInstance(failure_result, SuccessResult)
        self.assertEqual(failure_result.transfer_type, 'delete')
        self.assertTrue(failure_result.src.endswith(self.filename))
        self.assertIsNone(failure_result.dest)

        self.assertFalse(os.path.exists(full_filename))

    def test_submit_with_exception(self):
        fileinfo = FileInfo(
            src=self.filename, dest=None, operation_name='delete',
            src_type='local')
        # The file was never created so it should trigger an exception
        # when it is attempted to be deleted in the submitter.
        rval = self.transfer_request_submitter.submit(fileinfo)
        self.assertTrue(rval)

        queued_result = self.result_queue.get()
        self.assertIsInstance(queued_result, QueuedResult)
        self.assertEqual(queued_result.transfer_type, 'delete')
        self.assertTrue(queued_result.src.endswith(self.filename))
        self.assertIsNone(queued_result.dest)
        self.assertEqual(queued_result.total_transfer_size, 0)

        failure_result = self.result_queue.get()
        self.assertIsInstance(failure_result, FailureResult)
        self.assertEqual(failure_result.transfer_type, 'delete')
        self.assertTrue(failure_result.src.endswith(self.filename))
        self.assertIsNone(failure_result.dest)

    def test_dry_run(self):
        self.cli_params['dryrun'] = True
        fileinfo = FileInfo(
            src=self.filename, src_type='local',
            dest=self.filename, dest_type='local',
            operation_name='delete')
        self.transfer_request_submitter.submit(fileinfo)

        result = self.result_queue.get()
        self.assertIsInstance(result, DryRunResult)
        self.assertEqual(result.transfer_type, 'delete')
        self.assertTrue(result.src.endswith(self.filename))
        self.assertIsNone(result.dest)

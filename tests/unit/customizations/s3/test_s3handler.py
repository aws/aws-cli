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
import contextlib
import os
import signal
import stat

import pytest
from botocore.exceptions import ClientError
from s3transfer.manager import TransferManager

from awscli.compat import queue
from awscli.customizations.s3 import s3handler as s3handler_module
from awscli.customizations.s3.fileinfo import FileInfo
from awscli.customizations.s3.results import (
    CommandResultRecorder,
    DoneResultSubscriber,
    DryRunResult,
    FailureResult,
    ProgressResultSubscriber,
    QueuedResult,
    QueuedResultSubscriber,
    ResultProcessor,
    ResultRecorder,
    SuccessResult,
)
from awscli.customizations.s3.s3handler import (
    CopyRequestSubmitter,
    DeleteRequestSubmitter,
    DownloadRequestSubmitter,
    DownloadStreamRequestSubmitter,
    LocalDeleteRequestSubmitter,
    S3TransferHandler,
    S3TransferHandlerFactory,
    UploadRequestSubmitter,
    UploadStreamRequestSubmitter,
)
from awscli.customizations.s3.subscribers import (
    DeleteSourceFileSubscriber,
    DeleteSourceObjectSubscriber,
    DirectoryCreatorSubscriber,
    ExcludeAnnotationDirectiveSubscriber,
    ProvideETagSubscriber,
    ProvideFullObjectChecksumSubscriber,
    ProvideLastModifiedTimeSubscriber,
    ProvideSizeSubscriber,
    ProvideUploadContentTypeSubscriber,
    SetMetadataDirectivePropsSubscriber,
    SetTagsSubscriber,
)
from awscli.customizations.s3.transferconfig import RuntimeConfig
from awscli.customizations.s3.utils import (
    MAX_UPLOAD_SIZE,
    NonSeekableStream,
    StdoutBytesWriter,
    WarningResult,
)
from awscli.testutils import FileCreator, mock, unittest


def runtime_config(**kwargs):
    return RuntimeConfig().build_config(**kwargs)


class TestS3TransferHandlerFactory(unittest.TestCase):
    def setUp(self):
        self.cli_params = {}
        self.runtime_config = runtime_config()
        self.transfer_manager = mock.Mock()
        self.result_queue = queue.Queue()

    def test_call(self):
        factory = S3TransferHandlerFactory(self.cli_params)
        self.assertIsInstance(
            factory(self.transfer_manager, self.result_queue),
            S3TransferHandler,
        )


class TestS3TransferHandler(unittest.TestCase):
    def setUp(self):
        self.result_queue = queue.Queue()
        self.result_recorder = ResultRecorder()
        self.processed_results = []
        self.result_processor = ResultProcessor(
            self.result_queue,
            [self.result_recorder, self.processed_results.append],
        )
        self.command_result_recorder = CommandResultRecorder(
            self.result_queue, self.result_recorder, self.result_processor
        )

        self.transfer_manager = mock.Mock(spec=TransferManager)
        self.transfer_manager.__enter__ = mock.Mock()
        self.transfer_manager.__exit__ = mock.Mock()
        self.parameters = {}
        self.s3_transfer_handler = S3TransferHandler(
            self.transfer_manager,
            self.parameters,
            self.command_result_recorder,
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
                FileInfo(
                    src='filename', dest='bucket/key', operation_name='upload'
                )
            )

        self.s3_transfer_handler.call(fileinfos)
        self.assertEqual(
            self.transfer_manager.upload.call_count, num_transfers
        )

    def test_enqueue_downloads(self):
        fileinfos = []
        num_transfers = 5
        for _ in range(num_transfers):
            fileinfos.append(
                FileInfo(
                    src='bucket/key',
                    dest='filename',
                    compare_key='key',
                    operation_name='download',
                )
            )

        self.s3_transfer_handler.call(fileinfos)
        self.assertEqual(
            self.transfer_manager.download.call_count, num_transfers
        )

    def test_enqueue_copies(self):
        fileinfos = []
        num_transfers = 5
        for _ in range(num_transfers):
            fileinfos.append(
                FileInfo(
                    src='sourcebucket/sourcekey',
                    dest='bucket/key',
                    compare_key='key',
                    operation_name='copy',
                )
            )

        self.s3_transfer_handler.call(fileinfos)
        self.assertEqual(self.transfer_manager.copy.call_count, num_transfers)

    def test_exception_when_enqueuing(self):
        fileinfos = [
            FileInfo(
                src='filename', dest='bucket/key', operation_name='upload'
            )
        ]
        self.transfer_manager.__exit__.side_effect = Exception(
            'some exception'
        )
        command_result = self.s3_transfer_handler.call(fileinfos)
        # Exception should have been raised casing the command result to
        # have failed results of one.
        self.assertEqual(command_result, (1, 0))

    def test_enqueue_upload_stream(self):
        self.parameters['is_stream'] = True
        self.s3_transfer_handler.call(
            [FileInfo(src='-', dest='bucket/key', operation_name='upload')]
        )
        self.assertEqual(self.transfer_manager.upload.call_count, 1)
        upload_call_kwargs = self.transfer_manager.upload.call_args[1]
        self.assertIsInstance(upload_call_kwargs['fileobj'], NonSeekableStream)

    def test_enqueue_dowload_stream(self):
        self.parameters['is_stream'] = True
        self.s3_transfer_handler.call(
            [
                FileInfo(
                    src='bucket/key',
                    dest='-',
                    compare_key='key',
                    operation_name='download',
                )
            ]
        )
        self.assertEqual(self.transfer_manager.download.call_count, 1)
        download_call_kwargs = self.transfer_manager.download.call_args[1]
        self.assertIsInstance(
            download_call_kwargs['fileobj'], StdoutBytesWriter
        )

    def test_enqueue_deletes(self):
        fileinfos = []
        num_transfers = 5
        for _ in range(num_transfers):
            fileinfos.append(
                FileInfo(
                    src='bucket/key',
                    dest=None,
                    operation_name='delete',
                    src_type='s3',
                )
            )

        self.s3_transfer_handler.call(fileinfos)
        self.assertEqual(
            self.transfer_manager.delete.call_count, num_transfers
        )

    def test_enqueue_local_deletes(self):
        fileinfos = []
        num_transfers = 5
        for _ in range(num_transfers):
            fileinfos.append(
                FileInfo(
                    src='myfile',
                    dest=None,
                    operation_name='delete',
                    src_type='local',
                )
            )

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
                FileInfo(
                    src='bucket/key',
                    dest='filename',
                    compare_key='key',
                    operation_name='download',
                )
            )

        self.s3_transfer_handler.call(fileinfos)
        self.assertEqual(
            self.result_recorder.final_expected_files_transferred,
            num_transfers,
        )

    def test_notifies_total_submissions_accounts_for_skips(self):
        fileinfos = []
        num_transfers = 5
        for _ in range(num_transfers):
            fileinfos.append(
                FileInfo(
                    src='bucket/key',
                    dest='filename',
                    compare_key='key',
                    operation_name='download',
                )
            )

        # Add a fileinfo that should get skipped. To skip, we do a glacier
        # download.
        fileinfos.append(
            FileInfo(
                src='bucket/key',
                dest='filename',
                operation_name='download',
                compare_key='key',
                associated_response_data={'StorageClass': 'GLACIER'},
            )
        )
        self.s3_transfer_handler.call(fileinfos)
        # Since the last glacier download was skipped the final expected
        # total should be equal to the number of transfers provided in the
        # for loop.
        self.assertEqual(
            self.result_recorder.final_expected_files_transferred,
            num_transfers,
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
            self.transfer_manager, self.result_queue, self.cli_params
        )

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.filename,
            dest=self.bucket + '/' + self.key,
            operation_name='upload',
        )
        self.assertTrue(self.transfer_request_submitter.can_submit(fileinfo))
        fileinfo.operation_name = 'foo'
        self.assertFalse(self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket + '/' + self.key
        )
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
            ProvideETagSubscriber,
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
            src=self.filename, dest=self.bucket + '/' + self.key
        )
        # Set some extra argument like storage_class to make sure cli
        # params get mapped to request parameters.
        self.cli_params['storage_class'] = 'STANDARD_IA'
        self.transfer_request_submitter.submit(fileinfo)

        upload_call_kwargs = self.transfer_manager.upload.call_args[1]
        self.assertEqual(
            upload_call_kwargs['extra_args'], {'StorageClass': 'STANDARD_IA'}
        )

    def test_submit_when_content_type_specified(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket + '/' + self.key
        )
        self.cli_params['content_type'] = 'text/plain'
        self.transfer_request_submitter.submit(fileinfo)

        upload_call_kwargs = self.transfer_manager.upload.call_args[1]
        self.assertEqual(
            upload_call_kwargs['extra_args'], {'ContentType': 'text/plain'}
        )
        ref_subscribers = [
            ProvideSizeSubscriber,
            ProvideETagSubscriber,
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
            src=self.filename, dest=self.bucket + '/' + self.key
        )
        self.cli_params['guess_mime_type'] = False
        self.transfer_request_submitter.submit(fileinfo)

        upload_call_kwargs = self.transfer_manager.upload.call_args[1]
        ref_subscribers = [
            ProvideSizeSubscriber,
            ProvideETagSubscriber,
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
            src=self.filename,
            dest=self.bucket + '/' + self.key,
            size=MAX_UPLOAD_SIZE + 1,
        )
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
            self.transfer_manager, self.result_queue, self.cli_params
        )
        fileinfo = FileInfo(
            src=self.filename,
            src_type='local',
            operation_name='upload',
            dest=self.bucket + '/' + self.key,
            dest_type='s3',
        )
        self.transfer_request_submitter.submit(fileinfo)

        result = self.result_queue.get()
        self.assertIsInstance(result, DryRunResult)
        self.assertEqual(result.transfer_type, 'upload')
        self.assertTrue(result.src.endswith(self.filename))
        self.assertEqual(result.dest, 's3://' + self.bucket + '/' + self.key)

    def test_submit_move_adds_delete_source_subscriber(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket + '/' + self.key
        )
        self.cli_params['guess_mime_type'] = True  # Default settings
        self.cli_params['is_move'] = True
        self.transfer_request_submitter.submit(fileinfo)
        ref_subscribers = [
            ProvideSizeSubscriber,
            ProvideETagSubscriber,
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
            self.transfer_manager, self.result_queue, self.cli_params
        )

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
            src=self.bucket + '/' + self.key,
            dest=self.filename,
            operation_name='download',
        )
        self.assertTrue(self.transfer_request_submitter.can_submit(fileinfo))
        fileinfo.operation_name = 'foo'
        self.assertFalse(self.transfer_request_submitter.can_submit(fileinfo))

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
            ProvideETagSubscriber,
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
            {'SSECustomerAlgorithm': 'AES256', 'SSECustomerKey': 'mykey'},
        )

    def test_warn_glacier_for_incompatible(self):
        fileinfo = FileInfo(
            src=self.bucket + '/' + self.key,
            dest=self.filename,
            operation_name='download',
            associated_response_data={
                'StorageClass': 'GLACIER',
            },
        )
        future = self.transfer_request_submitter.submit(fileinfo)

        # A warning should have been submitted because it is a non-restored
        # glacier object.
        warning_result = self.result_queue.get()
        self.assertIsInstance(warning_result, WarningResult)
        self.assertIn(
            'Unable to perform download operations on GLACIER objects',
            warning_result.message,
        )

        # The transfer should have been skipped.
        self.assertIsNone(future)
        self.assert_no_downloads_happened()

    def test_not_warn_glacier_for_compatible(self):
        fileinfo = self.create_file_info(
            self.key,
            associated_response_data={
                'StorageClass': 'GLACIER',
                'Restore': 'ongoing-request="false"',
            },
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
            },
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
            src=self.bucket + '/' + self.key,
            dest=self.filename,
            operation_name='download',
            associated_response_data={
                'StorageClass': 'GLACIER',
            },
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

    def test_warn_and_ignore_on_leading_slash_parent_reference(self):
        fileinfo = self.create_file_info('/../foo.txt')
        future = self.transfer_request_submitter.submit(fileinfo)
        warning_result = self.result_queue.get()
        self.assertIsInstance(warning_result, WarningResult)
        self.assert_no_downloads_happened()

    def test_warn_and_ignore_on_leading_slash_stacked_parent_reference(self):
        fileinfo = self.create_file_info('/../../../foo/bar.txt')
        future = self.transfer_request_submitter.submit(fileinfo)
        warning_result = self.result_queue.get()
        self.assertIsInstance(warning_result, WarningResult)
        self.assert_no_downloads_happened()

    def test_warn_and_ignore_on_double_leading_slash_parent_reference(self):
        fileinfo = self.create_file_info('//../foo')
        future = self.transfer_request_submitter.submit(fileinfo)
        warning_result = self.result_queue.get()
        self.assertIsInstance(warning_result, WarningResult)
        self.assert_no_downloads_happened()

    def test_dry_run(self):
        self.cli_params['dryrun'] = True
        self.transfer_request_submitter = DownloadRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params
        )
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
            ProvideETagSubscriber,
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

    def test_skip_download_when_no_overwrite_and_file_exists(self):
        self.cli_params['no_overwrite'] = True
        fileinfo = self.create_file_info(self.key)
        with mock.patch('os.path.exists', return_value=True):
            future = self.transfer_request_submitter.submit(fileinfo)

        # Result Queue should be empty because it was specified to ignore no-overwrite warnings.
        self.assertTrue(self.result_queue.empty())
        # The transfer should be skipped, so future should be None
        self.assertIsNone(future)
        self.assert_no_downloads_happened()

    def test_proceed_download_when_no_overwrite_and_file_not_exists(self):
        self.cli_params['no_overwrite'] = True
        fileinfo = self.create_file_info(self.key)
        with mock.patch('os.path.exists', return_value=False):
            future = self.transfer_request_submitter.submit(fileinfo)
        # The transfer should proceed, so future should be the transfer manager's return value
        self.assertIs(self.transfer_manager.download.return_value, future)
        # And download should have happened
        self.assertEqual(len(self.transfer_manager.download.call_args_list), 1)

    def test_warn_if_file_exists_without_no_overwrite_flag(self):
        self.cli_params['no_overwrite'] = False
        fileinfo = self.create_file_info(self.key)
        with mock.patch('os.path.exists', return_value=True):
            future = self.transfer_request_submitter.submit(fileinfo)
        # The transfer should proceed, so future should be the transfer manager's return value
        self.assertIs(self.transfer_manager.download.return_value, future)
        # And download should have happened
        self.assertEqual(len(self.transfer_manager.download.call_args_list), 1)

    def test_submit_with_full_object_checksum(self):
        fileinfo = self.create_file_info(
            self.key,
            associated_response_data={
                'ChecksumType': 'FULL_OBJECT',
                'ChecksumCRC32': 'abc123==',
            },
        )
        self.transfer_request_submitter.submit(fileinfo)
        download_call_kwargs = self.transfer_manager.download.call_args[1]
        actual_subscribers = download_call_kwargs['subscribers']
        subscriber_types = [type(s) for s in actual_subscribers]
        self.assertIn(ProvideFullObjectChecksumSubscriber, subscriber_types)

    def test_submit_without_full_object_checksum(self):
        fileinfo = self.create_file_info(self.key)
        self.transfer_request_submitter.submit(fileinfo)
        download_call_kwargs = self.transfer_manager.download.call_args[1]
        actual_subscribers = download_call_kwargs['subscribers']
        subscriber_types = [type(s) for s in actual_subscribers]
        self.assertNotIn(ProvideFullObjectChecksumSubscriber, subscriber_types)

    def test_submit_with_composite_checksum_does_not_add_subscriber(self):
        fileinfo = self.create_file_info(
            self.key,
            associated_response_data={
                'ChecksumType': 'COMPOSITE',
                'ChecksumCRC32': 'abc123==-5',
            },
        )
        self.transfer_request_submitter.submit(fileinfo)
        download_call_kwargs = self.transfer_manager.download.call_args[1]
        actual_subscribers = download_call_kwargs['subscribers']
        subscriber_types = [type(s) for s in actual_subscribers]
        self.assertNotIn(ProvideFullObjectChecksumSubscriber, subscriber_types)


class TestCopyRequestSubmitter(BaseTransferRequestSubmitterTest):
    def setUp(self):
        super(TestCopyRequestSubmitter, self).setUp()
        self.source_bucket = 'mysourcebucket'
        self.source_key = 'mysourcekey'
        self.transfer_request_submitter = CopyRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params
        )

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.source_bucket + '/' + self.source_key,
            dest=self.bucket + '/' + self.key,
            operation_name='copy',
        )
        self.assertTrue(self.transfer_request_submitter.can_submit(fileinfo))
        fileinfo.operation_name = 'foo'
        self.assertFalse(self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        fileinfo = FileInfo(
            src=self.source_bucket + '/' + self.source_key,
            dest=self.bucket + '/' + self.key,
        )
        self.cli_params['guess_mime_type'] = True  # Default settings
        future = self.transfer_request_submitter.submit(fileinfo)
        self.assertIs(self.transfer_manager.copy.return_value, future)
        copy_call_kwargs = self.transfer_manager.copy.call_args[1]
        self.assertEqual(
            copy_call_kwargs['copy_source'],
            {'Bucket': self.source_bucket, 'Key': self.source_key},
        )
        self.assertEqual(copy_call_kwargs['bucket'], self.bucket)
        self.assertEqual(copy_call_kwargs['key'], self.key)
        self.assertEqual(copy_call_kwargs['extra_args'], {})

        # Make sure the subscriber applied are of the correct type and order
        ref_subscribers = [
            ProvideSizeSubscriber,
            ProvideETagSubscriber,
            QueuedResultSubscriber,
            SetMetadataDirectivePropsSubscriber,
            SetTagsSubscriber,
            ExcludeAnnotationDirectiveSubscriber,
            ProgressResultSubscriber,
            DoneResultSubscriber,
        ]
        actual_subscribers = copy_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_submit_with_extra_args(self):
        fileinfo = FileInfo(
            src=self.source_bucket + '/' + self.source_key,
            dest=self.bucket + '/' + self.key,
        )
        # Set some extra argument like storage_class to make sure cli
        # params get mapped to request parameters.
        self.cli_params['storage_class'] = 'STANDARD_IA'
        self.transfer_request_submitter.submit(fileinfo)

        copy_call_kwargs = self.transfer_manager.copy.call_args[1]
        self.assertEqual(
            copy_call_kwargs['extra_args'], {'StorageClass': 'STANDARD_IA'}
        )

    def test_submit_when_content_type_specified(self):
        fileinfo = FileInfo(
            src=self.source_bucket + '/' + self.source_key,
            dest=self.bucket + '/' + self.key,
        )
        self.cli_params['content_type'] = 'text/plain'
        self.transfer_request_submitter.submit(fileinfo)

        copy_call_kwargs = self.transfer_manager.copy.call_args[1]
        self.assertEqual(
            copy_call_kwargs['extra_args'], {'ContentType': 'text/plain'}
        )
        ref_subscribers = [
            ProvideSizeSubscriber,
            ProvideETagSubscriber,
            QueuedResultSubscriber,
            SetMetadataDirectivePropsSubscriber,
            SetTagsSubscriber,
            ExcludeAnnotationDirectiveSubscriber,
            ProgressResultSubscriber,
            DoneResultSubscriber,
        ]
        actual_subscribers = copy_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_metadata_directive_excludes_copy_props_subscribers(self):
        fileinfo = FileInfo(
            src=self.source_bucket + '/' + self.source_key,
            dest=self.bucket + '/' + self.key,
        )
        self.cli_params['copy_props'] = 'default'
        self.cli_params['metadata_directive'] = 'REPLACE'
        self.transfer_request_submitter.submit(fileinfo)

        copy_call_kwargs = self.transfer_manager.copy.call_args[1]
        ref_subscribers = [
            ProvideSizeSubscriber,
            ProvideETagSubscriber,
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
            src=self.source_bucket + '/' + self.source_key,
            dest=self.bucket + '/' + self.key,
            operation_name='copy',
            associated_response_data={
                'StorageClass': 'GLACIER',
            },
        )
        future = self.transfer_request_submitter.submit(fileinfo)

        # A warning should have been submitted because it is a non-restored
        # glacier object.
        warning_result = self.result_queue.get()
        self.assertIsInstance(warning_result, WarningResult)
        self.assertIn(
            'Unable to perform copy operations on GLACIER objects',
            warning_result.message,
        )

        # The transfer request should have never been sent therefore return
        # no future.
        self.assertIsNone(future)
        # The transfer should have been skipped.
        self.assertEqual(len(self.transfer_manager.copy.call_args_list), 0)

    def test_not_warn_glacier_for_compatible(self):
        fileinfo = FileInfo(
            src=self.source_bucket + '/' + self.source_key,
            dest=self.bucket + '/' + self.key,
            operation_name='copy',
            associated_response_data={
                'StorageClass': 'GLACIER',
                'Restore': 'ongoing-request="false"',
            },
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
            src=self.source_bucket + '/' + self.source_key,
            dest=self.bucket + '/' + self.key,
            operation_name='copy',
            associated_response_data={
                'StorageClass': 'GLACIER',
            },
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
            src=self.source_bucket + '/' + self.source_key,
            dest=self.bucket + '/' + self.key,
            operation_name='copy',
            associated_response_data={
                'StorageClass': 'GLACIER',
            },
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
            self.transfer_manager, self.result_queue, self.cli_params
        )
        fileinfo = FileInfo(
            src=self.source_bucket + '/' + self.source_key,
            src_type='s3',
            dest=self.bucket + '/' + self.key,
            dest_type='s3',
            operation_name='copy',
        )
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
            src=self.bucket + '/' + self.key,
        )
        self.cli_params['guess_mime_type'] = True  # Default settings
        self.cli_params['is_move'] = True
        self.transfer_request_submitter.submit(fileinfo)
        ref_subscribers = [
            ProvideSizeSubscriber,
            ProvideETagSubscriber,
            QueuedResultSubscriber,
            SetMetadataDirectivePropsSubscriber,
            SetTagsSubscriber,
            ExcludeAnnotationDirectiveSubscriber,
            DeleteSourceObjectSubscriber,
            ProgressResultSubscriber,
            DoneResultSubscriber,
        ]
        copy_call_kwargs = self.transfer_manager.copy.call_args[1]
        actual_subscribers = copy_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_file_exists_without_no_overwrite(self):
        self.cli_params['no_overwrite'] = False
        fileinfo = FileInfo(
            src=self.source_bucket + "/" + self.source_key,
            dest=self.bucket + "/" + self.key,
            operation_name='copy',
            size=100,
            source_client=mock.Mock(),
        )
        future = self.transfer_request_submitter.submit(fileinfo)
        # The transfer should proceed, so future should be the transfer manager's return value
        self.assertIs(self.transfer_manager.copy.return_value, future)
        self.assertEqual(len(self.transfer_manager.copy.call_args_list), 1)
        # Head should not be called when no_overwrite is false
        fileinfo.source_client.head_object.assert_not_called()


class TestUploadStreamRequestSubmitter(BaseTransferRequestSubmitterTest):
    def setUp(self):
        super(TestUploadStreamRequestSubmitter, self).setUp()
        self.filename = '-'
        self.cli_params['is_stream'] = True
        self.transfer_request_submitter = UploadStreamRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params
        )

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.filename,
            dest=self.bucket + '/' + self.key,
            operation_name='upload',
        )
        self.assertTrue(self.transfer_request_submitter.can_submit(fileinfo))
        self.cli_params['is_stream'] = False
        self.assertFalse(self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket + '/' + self.key
        )
        future = self.transfer_request_submitter.submit(fileinfo)
        self.assertIs(self.transfer_manager.upload.return_value, future)

        upload_call_kwargs = self.transfer_manager.upload.call_args[1]
        self.assertIsInstance(upload_call_kwargs['fileobj'], NonSeekableStream)
        self.assertEqual(upload_call_kwargs['bucket'], self.bucket)
        self.assertEqual(upload_call_kwargs['key'], self.key)
        self.assertEqual(upload_call_kwargs['extra_args'], {})

        ref_subscribers = [
            ProvideETagSubscriber,
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
            src=self.filename, dest=self.bucket + '/' + self.key
        )
        self.transfer_request_submitter.submit(fileinfo)
        upload_call_kwargs = self.transfer_manager.upload.call_args[1]

        ref_subscribers = [
            ProvideSizeSubscriber,
            ProvideETagSubscriber,
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
            self.transfer_manager, self.result_queue, self.cli_params
        )
        fileinfo = FileInfo(
            src=self.filename,
            src_type='local',
            operation_name='upload',
            dest=self.bucket + '/' + self.key,
            dest_type='s3',
        )
        self.transfer_request_submitter.submit(fileinfo)

        result = self.result_queue.get()
        self.assertIsInstance(result, DryRunResult)
        self.assertEqual(result.transfer_type, 'upload')
        self.assertEqual(result.dest, 's3://' + self.bucket + '/' + self.key)
        self.assertEqual(result.src, '-')


class TestDownloadRequestSubmitterNoFollowLinks(
    BaseTransferRequestSubmitterTest
):
    def setUp(self):
        super().setUp()
        # Drive qualified so that the root and the destinations built from it
        # agree on Windows, where abspath adds the current drive.
        self.root = os.path.abspath(os.path.join(os.sep, 'dest'))
        self.cli_params['dest'] = self.root
        self.cli_params['follow_symlinks'] = False
        self.transfer_request_submitter = DownloadRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params
        )

    def submit(self, dest, key, links=()):
        with mock.patch(
            'awscli.customizations.s3.s3handler.is_link',
            side_effect=lambda p: p in links,
        ):
            return self.transfer_request_submitter.submit(
                FileInfo(
                    src=self.bucket + '/' + key,
                    src_type='s3',
                    dest=dest,
                    dest_type='local',
                    operation_name='download',
                    compare_key=key,
                )
            )

    def test_skips_link_in_parent_directory(self):
        sub = os.path.join(self.root, 'sub')
        dest = os.path.join(sub, 'obj.txt')
        self.assertIsNone(self.submit(dest, 'sub/obj.txt', links=[sub]))
        self.assertEqual(self.transfer_manager.download.call_args_list, [])
        self.assertTrue(self.result_queue.empty())

    def test_skips_link_in_parent_directory_with_trailing_separator(self):
        sub = os.path.join(self.root, 'sub')
        self.assertIsNone(self.submit(sub + os.sep, 'sub/', links=[sub]))

    def test_skips_link_when_dest_root_is_filesystem_root(self):
        self.cli_params['dest'] = os.sep
        sub = os.path.join(self.root, 'sub')
        dest = os.path.join(sub, 'obj.txt')
        self.assertIsNone(self.submit(dest, 'dest/sub/obj.txt', links=[sub]))

    @unittest.skipIf(
        not hasattr(signal, 'SIGALRM'), 'Needs signal.alarm to stop a hang'
    )
    def test_terminates_when_dest_root_is_filesystem_root(self):
        # 'sync s3://bucket /' produces destinations of the form '//key', and
        # dirname('//') is '//' on POSIX, so without the fixpoint break the
        # walk never reaches the root and loops forever.
        self.cli_params['dest'] = os.sep
        dest = os.sep * 2 + 'a' + os.sep + 'b'
        with _time_limit(5):
            self.submit(dest, 'a/b')

    def test_skips_link_at_destination(self):
        dest = os.path.join(self.root, 'obj.txt')
        self.assertIsNone(self.submit(dest, 'obj.txt', links=[dest]))
        self.assertEqual(self.transfer_manager.download.call_args_list, [])

    def test_submits_when_nothing_is_a_link(self):
        dest = os.path.join(self.root, 'sub', 'obj.txt')
        self.assertIsNotNone(self.submit(dest, 'sub/obj.txt', links=[]))

    def test_skips_link_at_the_destination_root(self):
        dest = os.path.join(self.root, 'obj.txt')
        self.assertIsNone(self.submit(dest, 'obj.txt', links=[self.root]))
        self.assertEqual(self.transfer_manager.download.call_args_list, [])

    def test_submits_when_dest_is_the_root_and_a_link_is_above_it(self):
        # Single-file cp names the whole path, so there is nothing below the
        # root to walk. Without the below-root guard the walk would continue
        # past the root and reject a link anywhere above it, e.g. /var.
        above = os.path.dirname(self.root)
        self.cli_params['dest'] = self.root
        self.assertIsNotNone(self.submit(self.root, 'obj.txt', links=[above]))

    def test_skips_link_with_a_relative_destination_root(self):
        # cli_params['dest'] is the raw user string while fileinfo.dest is
        # absolute, so the root has to be resolved before they are compared.
        # Without that, 'aws s3 sync s3://bucket dest' checks nothing.
        self.cli_params['dest'] = 'dest'
        sub = os.path.join(os.path.abspath('dest'), 'sub')
        dest = os.path.join(sub, 'obj.txt')
        self.assertIsNone(self.submit(dest, 'sub/obj.txt', links=[sub]))

    def test_skips_deeply_nested_link(self):
        sub = os.path.join(self.root, 'a', 'b', 'sub')
        dest = os.path.join(sub, 'obj.txt')
        self.assertIsNone(self.submit(dest, 'a/b/sub/obj.txt', links=[sub]))

    def test_submits_when_a_link_is_above_the_destination_root(self):
        # Paths above the destination are not part of the transfer and are
        # commonly links, e.g. /tmp and /var on macOS.
        above = os.path.dirname(self.root)
        dest = os.path.join(self.root, 'obj.txt')
        self.assertIsNotNone(self.submit(dest, 'obj.txt', links=[above]))

    def test_submits_when_following_links(self):
        self.cli_params['follow_symlinks'] = True
        dest = os.path.join(self.root, 'sub', 'obj.txt')
        sub = os.path.join(self.root, 'sub')
        self.assertIsNotNone(self.submit(dest, 'sub/obj.txt', links=[sub]))

    def test_checks_the_destination_root_then_each_directory_below_it(self):
        sub = os.path.join(self.root, 'a', 'b')
        dest = os.path.join(sub, 'obj.txt')
        checked = []
        with mock.patch(
            'awscli.customizations.s3.s3handler.is_link',
            side_effect=lambda p: checked.append(p) or False,
        ):
            self.transfer_request_submitter.submit(
                FileInfo(
                    src=self.bucket + '/a/b/obj.txt',
                    src_type='s3',
                    dest=dest,
                    dest_type='local',
                    operation_name='download',
                    compare_key='a/b/obj.txt',
                )
            )
        self.assertEqual(
            checked,
            [
                self.root,
                os.path.join(self.root, 'a'),
                sub,
                dest,
            ],
        )

    def test_does_not_delete_source_object_for_skipped_move(self):
        self.cli_params['is_move'] = True
        sub = os.path.join(self.root, 'sub')
        dest = os.path.join(sub, 'obj.txt')
        self.assertIsNone(self.submit(dest, 'sub/obj.txt', links=[sub]))

        # A submitted move attaches the subscriber that deletes the source
        # object, so assert the skip path never builds one.
        self.assertIsNotNone(self.submit(dest, 'sub/obj.txt', links=[]))
        subscribers = self.transfer_manager.download.call_args[1][
            'subscribers'
        ]
        self.assertTrue(
            any(
                isinstance(s, DeleteSourceObjectSubscriber)
                for s in subscribers
            )
        )


@contextlib.contextmanager
def _time_limit(seconds):
    """Fails instead of hanging if the body does not finish in time."""

    def _raise(*args):
        raise AssertionError('timed out, likely a non-terminating loop')

    previous = signal.signal(signal.SIGALRM, _raise)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


MOUNT_POINT_TAG = 0xA0000003


@contextlib.contextmanager
def windows_reparse_tag(tag):
    """Fakes a Windows filesystem reporting a reparse tag for a path.

    ``stat.IO_REPARSE_TAG_MOUNT_POINT`` only exists on Windows, so it is
    created here to let these run everywhere. ``test_junction_tag_constant``
    covers the real name, which this would otherwise hide.
    """
    with (
        mock.patch('os.path.islink', return_value=False),
        mock.patch.object(s3handler_module, 'is_windows', True),
        mock.patch.object(
            s3handler_module.stat,
            'IO_REPARSE_TAG_MOUNT_POINT',
            MOUNT_POINT_TAG,
            create=True,
        ),
        mock.patch('os.lstat', return_value=mock.Mock(st_reparse_tag=tag)),
    ):
        yield


@pytest.mark.skipif(
    not hasattr(stat, 'IO_REPARSE_TAG_MOUNT_POINT'),
    reason='Reparse tags only exist on Windows',
)
def test_junction_tag_constant_matches_the_platform():
    # Guards against a typo in the constant or attribute name, which
    # is_link would otherwise swallow and report as "not a link".
    assert stat.IO_REPARSE_TAG_MOUNT_POINT == MOUNT_POINT_TAG
    assert hasattr(os.lstat(os.getcwd()), 'st_reparse_tag')


def test_is_link_for_symlink():
    with mock.patch('os.path.islink', return_value=True):
        assert s3handler_module.is_link('anything')


def test_is_link_for_plain_path():
    with mock.patch('os.path.islink', return_value=False):
        assert not s3handler_module.is_link('anything')


def test_is_link_for_windows_junction():
    # os.path.islink is False for a junction, so the reparse tag is what
    # identifies it. Junctions need no elevation to create, unlike symlinks,
    # so missing them would leave the easier vector open.
    with windows_reparse_tag(MOUNT_POINT_TAG):
        assert s3handler_module.is_link('junction')


@pytest.mark.parametrize(
    'tag',
    [
        0xA000000C,  # IO_REPARSE_TAG_SYMLINK, already covered by islink
        0xA000001D,  # IO_REPARSE_TAG_APPEXECLINK, a Store app stub
        0x9000001A,  # IO_REPARSE_TAG_CLOUD, a OneDrive placeholder
    ],
)
def test_is_link_for_other_reparse_tags(tag):
    with windows_reparse_tag(tag):
        assert not s3handler_module.is_link('reparse-point')


def test_is_link_for_missing_path():
    with (
        mock.patch('os.path.islink', return_value=False),
        mock.patch.object(s3handler_module, 'is_windows', True),
        mock.patch('os.lstat', side_effect=OSError()),
    ):
        assert not s3handler_module.is_link('missing')


def test_is_link_does_not_read_reparse_tag_off_windows():
    with (
        mock.patch('os.path.islink', return_value=False),
        mock.patch.object(s3handler_module, 'is_windows', False),
        mock.patch('os.lstat') as lstat,
    ):
        assert not s3handler_module.is_link('path')
        assert not lstat.called


class TestDownloadStreamRequestSubmitter(BaseTransferRequestSubmitterTest):
    def setUp(self):
        super(TestDownloadStreamRequestSubmitter, self).setUp()
        self.filename = '-'
        self.cli_params['is_stream'] = True
        self.transfer_request_submitter = DownloadStreamRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params
        )

    def test_submits_when_a_link_shares_the_stream_dest_name(self):
        # '-' resolves against the working directory like any other
        # destination, so a link of that name must not cause a skip.
        self.cli_params['follow_symlinks'] = False
        self.cli_params['dest'] = self.filename
        fileinfo = FileInfo(
            src=self.bucket + '/' + self.key,
            dest=self.filename,
            compare_key=self.key,
        )
        with mock.patch(
            'awscli.customizations.s3.s3handler.is_link', return_value=True
        ):
            future = self.transfer_request_submitter.submit(fileinfo)
        self.assertIs(self.transfer_manager.download.return_value, future)

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.bucket + '/' + self.key,
            dest=self.filename,
            operation_name='download',
        )
        self.assertTrue(self.transfer_request_submitter.can_submit(fileinfo))
        self.cli_params['is_stream'] = False
        self.assertFalse(self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        fileinfo = FileInfo(
            src=self.bucket + '/' + self.key,
            dest=self.filename,
            compare_key=self.key,
        )
        future = self.transfer_request_submitter.submit(fileinfo)
        self.assertIs(self.transfer_manager.download.return_value, future)

        download_call_kwargs = self.transfer_manager.download.call_args[1]
        self.assertIsInstance(
            download_call_kwargs['fileobj'], StdoutBytesWriter
        )
        self.assertEqual(download_call_kwargs['bucket'], self.bucket)
        self.assertEqual(download_call_kwargs['key'], self.key)
        self.assertEqual(download_call_kwargs['extra_args'], {})

        ref_subscribers = [
            ProvideETagSubscriber,
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
            self.transfer_manager, self.result_queue, self.cli_params
        )
        fileinfo = FileInfo(
            dest=self.filename,
            dest_type='local',
            operation_name='download',
            src=self.bucket + '/' + self.key,
            src_type='s3',
            compare_key=self.key,
        )
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
            self.transfer_manager, self.result_queue, self.cli_params
        )

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.bucket + '/' + self.key,
            dest=None,
            operation_name='delete',
            src_type='s3',
        )
        self.assertTrue(self.transfer_request_submitter.can_submit(fileinfo))
        fileinfo.operation_name = 'foo'
        self.assertFalse(self.transfer_request_submitter.can_submit(fileinfo))

    def test_cannot_submit_local_deletes(self):
        fileinfo = FileInfo(
            src=self.bucket + '/' + self.key,
            dest=None,
            operation_name='delete',
            src_type='local',
        )
        self.assertFalse(self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        fileinfo = FileInfo(
            src=self.bucket + '/' + self.key,
            dest=None,
            operation_name='delete',
        )
        future = self.transfer_request_submitter.submit(fileinfo)
        self.assertIs(self.transfer_manager.delete.return_value, future)

        delete_call_kwargs = self.transfer_manager.delete.call_args[1]
        self.assertEqual(delete_call_kwargs['bucket'], self.bucket)
        self.assertEqual(delete_call_kwargs['key'], self.key)
        self.assertEqual(delete_call_kwargs['extra_args'], {})

        ref_subscribers = [
            ProvideETagSubscriber,
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
            self.transfer_manager, self.result_queue, self.cli_params
        )
        fileinfo = FileInfo(
            src=self.bucket + '/' + self.key,
            src_type='s3',
            dest=self.bucket + '/' + self.key,
            dest_type='s3',
            operation_name='delete',
        )
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
            self.transfer_manager, self.result_queue, self.cli_params
        )
        self.file_creator = FileCreator()

    def tearDown(self):
        super(TestLocalDeleteRequestSubmitter, self).tearDown()
        self.file_creator.remove_all()

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.filename,
            dest=None,
            operation_name='delete',
            src_type='local',
        )
        self.assertTrue(self.transfer_request_submitter.can_submit(fileinfo))
        fileinfo.operation_name = 'foo'
        self.assertFalse(self.transfer_request_submitter.can_submit(fileinfo))

    def test_cannot_submit_remote_deletes(self):
        fileinfo = FileInfo(
            src=self.filename,
            dest=None,
            operation_name='delete',
            src_type='s3',
        )
        self.assertFalse(self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        full_filename = self.file_creator.create_file(self.filename, 'content')
        fileinfo = FileInfo(
            src=full_filename,
            dest=None,
            operation_name='delete',
            src_type='local',
        )
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
            src=self.filename,
            dest=None,
            operation_name='delete',
            src_type='local',
        )
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
            src=self.filename,
            src_type='local',
            dest=self.filename,
            dest_type='local',
            operation_name='delete',
        )
        self.transfer_request_submitter.submit(fileinfo)

        result = self.result_queue.get()
        self.assertIsInstance(result, DryRunResult)
        self.assertEqual(result.transfer_type, 'delete')
        self.assertTrue(result.src.endswith(self.filename))
        self.assertIsNone(result.dest)

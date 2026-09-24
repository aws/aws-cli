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
from awscli.testutils import FileCreator, mock, skip_if_windows, unittest


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

    def test_skips_link_at_destination(self):
        dest = os.path.join(self.root, 'obj.txt')
        self.assertIsNone(self.submit(dest, 'obj.txt', links=[dest]))
        self.assertEqual(self.transfer_manager.download.call_args_list, [])

    def test_submits_when_nothing_is_a_link(self):
        dest = os.path.join(self.root, 'sub', 'obj.txt')
        self.assertIsNotNone(self.submit(dest, 'sub/obj.txt', links=[]))

    def test_does_not_check_the_destination_root(self):
        dest = os.path.join(self.root, 'obj.txt')
        self.assertIsNotNone(self.submit(dest, 'obj.txt', links=[self.root]))


MOUNT_POINT_TAG = 0xA0000003


@contextlib.contextmanager
def windows_reparse_tag(tag):
    """Fakes a Windows filesystem reporting a reparse tag for a path."""
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


@skip_if_windows('Symlink tests only supported on mac/linux')
class TestDownloadRequestSubmitterNoFollowSymlinks(
    BaseTransferRequestSubmitterTest
):
    def setUp(self):
        super().setUp()
        self.files = FileCreator()
        self.root = os.path.join(self.files.rootdir, 'dest')
        os.makedirs(self.root)
        self.cli_params['dest'] = self.root
        self.cli_params['follow_symlinks'] = False
        self.transfer_request_submitter = DownloadRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params
        )
        self.outside = os.path.join(self.files.rootdir, 'outside')
        os.makedirs(self.outside)

    def tearDown(self):
        super().tearDown()
        self.files.remove_all()

    def submit(self, dest, key='mykey'):
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

    def assert_skipped(self, dest, key='mykey'):
        self.assertIsNone(self.submit(dest, key))
        self.assertEqual(self.transfer_manager.download.call_args_list, [])
        # Skips are silent so that the exit code is unaffected.
        self.assertTrue(self.result_queue.empty())

    def assert_submitted(self, dest, key='mykey'):
        self.assertIsNotNone(self.submit(dest, key))
        self.assertEqual(len(self.transfer_manager.download.call_args_list), 1)

    def test_skips_dest_that_is_symlink(self):
        target = self.files.create_file('target.txt', 'contents')
        dest = os.path.join(self.root, 'link.txt')
        os.symlink(target, dest)
        self.assert_skipped(dest)

    def test_skips_dest_under_symlinked_directory(self):
        os.symlink(self.outside, os.path.join(self.root, 'sub'))
        self.assert_skipped(
            os.path.join(self.root, 'sub', 'obj.txt'), key='sub/obj.txt'
        )

    def test_skips_dest_with_parent_reference_after_symlink(self):
        # os.path.relpath would normalize 'link/..' away, hiding the symlink
        # that the kernel resolves first.
        os.symlink(self.outside, os.path.join(self.root, 'link'))
        self.assert_skipped(
            os.path.join(self.root, 'link', os.pardir, 'obj.txt'),
            key='link/../obj.txt',
        )

    def test_skips_dest_with_parent_reference_and_no_symlink(self):
        # Conservative: a parent reference is skipped even with no symlink
        # present, because whether one is reachable through it cannot be
        # determined before the download creates the missing directories.
        os.makedirs(os.path.join(self.root, 'sub'))
        self.assert_skipped(
            os.path.join(self.root, 'sub', os.pardir, 'obj.txt'),
            key='sub/../obj.txt',
        )

    def test_handles_dest_root_of_filesystem_root(self):
        # A root of os.sep must not send the walk into an endless loop. Every
        # path below the root is in scope, so the outermost symlink is the one
        # reported, which on macOS is /var rather than the one created here.
        self.cli_params['dest'] = os.sep
        os.symlink(self.outside, os.path.join(self.root, 'sub'))
        dest = os.path.join(self.root, 'sub', 'obj.txt')
        found = self.transfer_request_submitter._find_symlink_in_dest_path(
            dest
        )
        self.assertIsNotNone(found)
        self.assertTrue(dest.startswith(found))

    def test_skips_dest_under_deeply_nested_symlinked_directory(self):
        os.makedirs(os.path.join(self.root, 'a', 'b'))
        os.symlink(self.outside, os.path.join(self.root, 'a', 'b', 'sub'))
        self.assert_skipped(
            os.path.join(self.root, 'a', 'b', 'sub', 'obj.txt'),
            key='a/b/sub/obj.txt',
        )

    def test_submits_when_dest_root_is_symlink(self):
        # The root is named by the user rather than derived from an object
        # key, and is commonly a symlink, e.g. /tmp on macOS. Skipping it
        # would make the whole command a silent no-op.
        root_link = os.path.join(self.files.rootdir, 'rootlink')
        os.symlink(self.outside, root_link)
        self.cli_params['dest'] = root_link
        self.assert_submitted(
            os.path.join(root_link, 'obj.txt'), key='obj.txt'
        )

    def test_submits_when_dest_itself_is_symlink_named_by_user(self):
        # Single-file cp: the user typed the whole path, so it is treated the
        # same as a symlinked destination root.
        target = self.files.create_file('target.txt', 'contents')
        dest = os.path.join(self.files.rootdir, 'filelink')
        os.symlink(target, dest)
        self.cli_params['dest'] = dest
        self.assert_submitted(dest)

    def test_skips_symlink_below_symlinked_dest_root(self):
        root_link = os.path.join(self.files.rootdir, 'rootlink')
        os.symlink(self.root, root_link)
        os.symlink(self.outside, os.path.join(self.root, 'sub'))
        self.cli_params['dest'] = root_link
        self.assert_skipped(
            os.path.join(root_link, 'sub', 'obj.txt'), key='sub/obj.txt'
        )

    def test_skips_symlink_reached_through_missing_parent_reference(self):
        # os.path.islink cannot resolve a path through a directory that does
        # not exist yet, and the download creates missing directories after
        # this check runs, so a parent reference is never followed.
        os.symlink(self.outside, os.path.join(self.root, 'b'))
        self.assert_skipped(
            os.path.join(self.root, 'a', os.pardir, 'b', 'obj.txt'),
            key='a/../b/obj.txt',
        )

    def test_skips_with_relative_dest_root(self):
        # cli_params['dest'] is the raw user string, so a relative destination
        # must still be resolved before it is compared against fileinfo.dest.
        os.symlink(self.outside, os.path.join(self.root, 'sub'))
        with mock.patch('os.getcwd', return_value=self.files.rootdir):
            self.cli_params['dest'] = 'dest'
            self.assert_skipped(
                os.path.join(self.root, 'sub', 'obj.txt'), key='sub/obj.txt'
            )

    def test_submits_dest_with_no_symlinks(self):
        os.makedirs(os.path.join(self.root, 'sub'))
        self.assert_submitted(
            os.path.join(self.root, 'sub', 'obj.txt'), key='sub/obj.txt'
        )

    def test_submits_when_symlink_is_above_dest_root(self):
        link_to_root = os.path.join(self.files.rootdir, 'rootlink')
        os.symlink(self.root, link_to_root)
        nested = os.path.join(link_to_root, 'sub')
        os.makedirs(nested)
        self.cli_params['dest'] = nested
        self.assert_submitted(os.path.join(nested, 'obj.txt'), key='obj.txt')

    def test_submits_when_following_symlinks(self):
        self.cli_params['follow_symlinks'] = True
        target = self.files.create_file('target.txt', 'contents')
        dest = os.path.join(self.root, 'link.txt')
        os.symlink(target, dest)
        self.assert_submitted(dest)

    def test_does_not_delete_source_object_for_skipped_move(self):
        self.cli_params['is_move'] = True
        os.symlink(self.outside, os.path.join(self.root, 'sub'))
        dest = os.path.join(self.root, 'sub', 'obj.txt')
        self.assert_skipped(dest, key='sub/obj.txt')

        # A submitted move attaches the subscriber that deletes the source
        # object, so assert the skip path never builds one.
        self.cli_params['follow_symlinks'] = True
        self.assert_submitted(dest, key='sub/obj.txt')
        subscribers = self.transfer_manager.download.call_args[1][
            'subscribers'
        ]
        self.assertTrue(
            any(
                isinstance(s, DeleteSourceObjectSubscriber)
                for s in subscribers
            )
        )

    def test_checks_each_directory_below_the_dest_root(self):
        sub = os.path.join(self.root, 'a', 'b')
        os.makedirs(sub)
        dest = os.path.join(sub, 'obj.txt')
        with mock.patch(
            'awscli.customizations.s3.s3handler.os.path.islink',
            side_effect=os.path.islink,
        ) as islink:
            self.submit(dest, key='a/b/obj.txt')
        # Root-most first, so the outermost symlink is reported, and the
        # destination root itself is never checked.
        self.assertEqual(
            [call[0][0] for call in islink.call_args_list],
            [os.path.join(self.root, 'a'), sub, dest],
        )


class TestDownloadStreamRequestSubmitter(BaseTransferRequestSubmitterTest):
    def setUp(self):
        super(TestDownloadStreamRequestSubmitter, self).setUp()
        self.filename = '-'
        self.cli_params['is_stream'] = True
        self.transfer_request_submitter = DownloadStreamRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params
        )

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

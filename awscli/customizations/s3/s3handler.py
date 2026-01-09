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
import logging
import os

from s3transfer.manager import TransferManager

from awscli.customizations.s3.utils import (
    human_readable_size, MAX_UPLOAD_SIZE, find_bucket_key, relative_path,
    create_warning, NonSeekableStream)
from awscli.customizations.s3.transferconfig import \
    create_transfer_config_from_runtime_config
from awscli.customizations.s3.results import UploadResultSubscriber
from awscli.customizations.s3.results import DownloadResultSubscriber
from awscli.customizations.s3.results import CopyResultSubscriber
from awscli.customizations.s3.results import UploadStreamResultSubscriber
from awscli.customizations.s3.results import DownloadStreamResultSubscriber
from awscli.customizations.s3.results import DeleteResultSubscriber
from awscli.customizations.s3.results import QueuedResult
from awscli.customizations.s3.results import SuccessResult
from awscli.customizations.s3.results import FailureResult
from awscli.customizations.s3.results import DryRunResult
from awscli.customizations.s3.results import ResultRecorder
from awscli.customizations.s3.results import ResultPrinter
from awscli.customizations.s3.results import OnlyShowErrorsResultPrinter
from awscli.customizations.s3.results import NoProgressResultPrinter
from awscli.customizations.s3.results import ResultProcessor
from awscli.customizations.s3.results import CommandResultRecorder
from awscli.customizations.s3.utils import RequestParamsMapper
from awscli.customizations.s3.utils import StdoutBytesWriter
from awscli.customizations.s3.utils import ProvideSizeSubscriber
from awscli.customizations.s3.utils import ProvideETagSubscriber
from awscli.customizations.s3.utils import ProvideUploadContentTypeSubscriber
from awscli.customizations.s3.utils import ProvideCopyContentTypeSubscriber
from awscli.customizations.s3.utils import ProvideLastModifiedTimeSubscriber
from awscli.customizations.s3.utils import DirectoryCreatorSubscriber
from awscli.customizations.s3.utils import DeleteSourceFileSubscriber
from awscli.customizations.s3.utils import DeleteSourceObjectSubscriber
from awscli.customizations.s3.utils import DeleteCopySourceObjectSubscriber
from awscli.customizations.s3.utils import CaseConflictCleanupSubscriber
from awscli.compat import get_binary_stdin


LOGGER = logging.getLogger(__name__)


class S3TransferHandlerFactory(object):
    MAX_IN_MEMORY_CHUNKS = 6

    def __init__(self, cli_params, runtime_config):
        """Factory for S3TransferHandlers

        :type cli_params: dict
        :param cli_params: The parameters provide to the CLI command

        :type runtime_config: RuntimeConfig
        :param runtime_config: The runtime config for the CLI command
            being run
        """
        self._cli_params = cli_params
        self._runtime_config = runtime_config

    def __call__(self, client, result_queue):
        """Creates a S3TransferHandler instance

        :type client: botocore.client.Client
        :param client: The client to power the S3TransferHandler

        :type result_queue: queue.Queue
        :param result_queue: The result queue to be used to process results
            for the S3TransferHandler

        :returns: A S3TransferHandler instance
        """
        transfer_config = create_transfer_config_from_runtime_config(
            self._runtime_config)
        transfer_config.max_in_memory_upload_chunks = self.MAX_IN_MEMORY_CHUNKS
        transfer_config.max_in_memory_download_chunks = \
            self.MAX_IN_MEMORY_CHUNKS

        transfer_manager = TransferManager(client, transfer_config)

        LOGGER.debug(
            "Using a multipart threshold of %s and a part size of %s",
            transfer_config.multipart_threshold,
            transfer_config.multipart_chunksize
        )
        result_recorder = ResultRecorder()
        result_processor_handlers = [result_recorder]
        self._add_result_printer(result_recorder, result_processor_handlers)
        result_processor = ResultProcessor(
            result_queue, result_processor_handlers)
        command_result_recorder = CommandResultRecorder(
            result_queue, result_recorder, result_processor)

        return S3TransferHandler(
            transfer_manager, self._cli_params, command_result_recorder)

    def _add_result_printer(self, result_recorder, result_processor_handlers):
        if self._cli_params.get('quiet'):
            return
        elif self._cli_params.get('only_show_errors'):
            result_printer = OnlyShowErrorsResultPrinter(result_recorder)
        elif self._cli_params.get('is_stream'):
            result_printer = OnlyShowErrorsResultPrinter(result_recorder)
        elif not self._cli_params.get('progress'):
            result_printer = NoProgressResultPrinter(result_recorder)
        else:
            result_printer = ResultPrinter(result_recorder)
        result_processor_handlers.append(result_printer)


class S3TransferHandler(object):
    def __init__(self, transfer_manager, cli_params, result_command_recorder):
        """Backend for performing S3 transfers

        :type transfer_manager: s3transfer.manager.TransferManager
        :param transfer_manager: Transfer manager to use for transfers

        :type cli_params: dict
        :param cli_params: The parameters passed to the CLI command in the
            form of a dictionary

        :type result_command_recorder: ResultCommandRecorder
        :param result_command_recorder: The result command recorder to be
            used to get the final result of the transfer
        """
        self._transfer_manager = transfer_manager
        # TODO: Ideally the s3 transfer handler should not need to know
        # about the result command recorder. It really only needs an interface
        # for adding results to the queue. When all of the commands have
        # converted to use this transfer handler, an effort should be made
        # to replace the passing of a result command recorder with an
        # abstraction to enqueue results.
        self._result_command_recorder = result_command_recorder

        submitter_args = (
            self._transfer_manager, self._result_command_recorder.result_queue,
            cli_params
        )
        self._submitters = [
            UploadStreamRequestSubmitter(*submitter_args),
            DownloadStreamRequestSubmitter(*submitter_args),
            UploadRequestSubmitter(*submitter_args),
            DownloadRequestSubmitter(*submitter_args),
            CopyRequestSubmitter(*submitter_args),
            DeleteRequestSubmitter(*submitter_args),
            LocalDeleteRequestSubmitter(*submitter_args)
        ]

    def call(self, fileinfos):
        """Process iterable of FileInfos for transfer

        :type fileinfos: iterable of FileInfos
        param fileinfos: Set of FileInfos to submit to underlying transfer
            request submitters to make transfer API calls to S3

        :rtype: CommandResult
        :returns: The result of the command that specifies the number of
            failures and warnings encountered.
        """
        with self._result_command_recorder:
            with self._transfer_manager:
                total_submissions = 0
                for fileinfo in fileinfos:
                    for submitter in self._submitters:
                        if submitter.can_submit(fileinfo):
                            if submitter.submit(fileinfo):
                                total_submissions += 1
                            break
                self._result_command_recorder.notify_total_submissions(
                    total_submissions)
        return self._result_command_recorder.get_command_result()


class BaseTransferRequestSubmitter(object):
    REQUEST_MAPPER_METHOD = None
    RESULT_SUBSCRIBER_CLASS = None

    def __init__(self, transfer_manager, result_queue, cli_params):
        """Submits transfer requests to the TransferManager

        Given a FileInfo object and provided CLI parameters, it will add the
        necessary extra arguments and subscribers in making a call to the
        TransferManager.

        :type transfer_manager: s3transfer.manager.TransferManager
        :param transfer_manager: The underlying transfer manager

        :type result_queue: queue.Queue
        :param result_queue: The result queue to use

        :type cli_params: dict
        :param cli_params: The associated CLI parameters passed in to the
            command as a dictionary.
        """
        self._transfer_manager = transfer_manager
        self._result_queue = result_queue
        self._cli_params = cli_params

    def submit(self, fileinfo):
        """Submits a transfer request based on the FileInfo provided

        There is no guarantee that the transfer request will be made on
        behalf of the fileinfo as a fileinfo may be skipped based on
        circumstances in which the transfer is not possible.

        :type fileinfo: awscli.customizations.s3.fileinfo.FileInfo
        :param fileinfo: The FileInfo to be used to submit a transfer
            request to the underlying transfer manager.

        :rtype: s3transfer.futures.TransferFuture
        :returns: A TransferFuture representing the transfer if it the
            transfer was submitted. If it was not submitted nothing
            is returned.
        """
        should_skip = self._warn_and_signal_if_skip(fileinfo)
        if not should_skip:
            return self._do_submit(fileinfo)

    def can_submit(self, fileinfo):
        """Checks whether it can submit a particular FileInfo

        :type fileinfo: awscli.customizations.s3.fileinfo.FileInfo
        :param fileinfo: The FileInfo to check if the transfer request
            submitter can handle.

        :returns: True if it can use the provided FileInfo to make a transfer
            request to the underlying transfer manager. False, otherwise.
        """
        raise NotImplementedError('can_submit()')

    def _do_submit(self, fileinfo):
        extra_args = {}
        if self.REQUEST_MAPPER_METHOD:
            self.REQUEST_MAPPER_METHOD(extra_args, self._cli_params)
        subscribers = []
        self._add_additional_subscribers(subscribers, fileinfo)
        # The result subscriber class should always be the last registered
        # subscriber to ensure it is not missing any information that
        # may have been added in a different subscriber such as size.
        if self.RESULT_SUBSCRIBER_CLASS:
            result_kwargs = {'result_queue': self._result_queue}
            if self._cli_params.get('is_move', False):
                result_kwargs['transfer_type'] = 'move'
            subscribers.append(self.RESULT_SUBSCRIBER_CLASS(**result_kwargs))

        if not self._cli_params.get('dryrun'):
            return self._submit_transfer_request(
                fileinfo, extra_args, subscribers)
        else:
            self._submit_dryrun(fileinfo)

    def _submit_dryrun(self, fileinfo):
        transfer_type = fileinfo.operation_name
        if self._cli_params.get('is_move', False):
            transfer_type = 'move'
        src, dest = self._format_src_dest(fileinfo)
        self._result_queue.put(DryRunResult(
            transfer_type=transfer_type, src=src, dest=dest))

    def _add_additional_subscribers(self, subscribers, fileinfo):
        pass

    def _submit_transfer_request(self, fileinfo, extra_args, subscribers):
        raise NotImplementedError('_submit_transfer_request()')

    def _warn_and_signal_if_skip(self, fileinfo):
        for warning_handler in self._get_warning_handlers():
            if warning_handler(fileinfo):
                # On the first warning handler that returns a signal to skip
                # immediately propagate this signal and no longer check
                # the other warning handlers as no matter what the file will
                # be skipped.
                return True

    def _get_warning_handlers(self):
        # Returns a list of warning handlers, which are callables that
        # take in a single parameter representing a FileInfo. It will then
        # add a warning to result_queue if needed and return True if
        # that FileInfo should be skipped.
        return []

    def _should_inject_content_type(self):
        return (
            self._cli_params.get('guess_mime_type') and
            not self._cli_params.get('content_type')
        )

    def _warn_glacier(self, fileinfo):
        if not self._cli_params.get('force_glacier_transfer'):
            if not fileinfo.is_glacier_compatible():
                LOGGER.debug(
                    'Encountered glacier object s3://%s. Not performing '
                    '%s on object.' % (fileinfo.src, fileinfo.operation_name))
                if not self._cli_params.get('ignore_glacier_warnings'):
                    warning = create_warning(
                        's3://'+fileinfo.src,
                        'Object is of storage class GLACIER. Unable to '
                        'perform %s operations on GLACIER objects. You must '
                        'restore the object to be able to perform the '
                        'operation. See aws s3 %s help for additional '
                        'parameter options to ignore or force these '
                        'transfers.' %
                        (fileinfo.operation_name, fileinfo.operation_name)
                    )
                    self._result_queue.put(warning)
                return True
        return False

    def _warn_parent_reference(self, fileinfo):
        # normpath() will use the OS path separator so we
        # need to take that into account when checking for a parent prefix.
        parent_prefix = '..' + os.path.sep
        escapes_cwd = os.path.normpath(fileinfo.compare_key).startswith(
            parent_prefix)
        if escapes_cwd:
            warning = create_warning(
                fileinfo.compare_key, "File references a parent directory.")
            self._result_queue.put(warning)
            return True
        return False

    def _format_src_dest(self, fileinfo):
        """Returns formatted versions of a fileinfos source and destination."""
        raise NotImplementedError('_format_src_dest')

    def _format_local_path(self, path):
        return relative_path(path)

    def _format_s3_path(self, path):
        if path.startswith('s3://'):
            return path
        return 's3://' + path


class UploadRequestSubmitter(BaseTransferRequestSubmitter):
    REQUEST_MAPPER_METHOD = RequestParamsMapper.map_put_object_params
    RESULT_SUBSCRIBER_CLASS = UploadResultSubscriber

    def can_submit(self, fileinfo):
        return fileinfo.operation_name == 'upload'

    def _add_additional_subscribers(self, subscribers, fileinfo):
        subscribers.append(ProvideSizeSubscriber(fileinfo.size))
        if self._should_inject_content_type():
            subscribers.append(ProvideUploadContentTypeSubscriber())
        if self._cli_params.get('is_move', False):
            subscribers.append(DeleteSourceFileSubscriber())

    def _submit_transfer_request(self, fileinfo, extra_args, subscribers):
        bucket, key = find_bucket_key(fileinfo.dest)
        filein = self._get_filein(fileinfo)
        return self._transfer_manager.upload(
            fileobj=filein, bucket=bucket, key=key,
            extra_args=extra_args, subscribers=subscribers
        )

    def _get_filein(self, fileinfo):
        return fileinfo.src

    def _get_warning_handlers(self):
        return [self._warn_if_too_large]

    def _warn_if_too_large(self, fileinfo):
        if getattr(fileinfo, 'size') and fileinfo.size > MAX_UPLOAD_SIZE:
            file_path = relative_path(fileinfo.src)
            warning_message = (
                "File %s exceeds s3 upload limit of %s." % (
                    file_path, human_readable_size(MAX_UPLOAD_SIZE)))
            warning = create_warning(
                file_path, warning_message, skip_file=False)
            self._result_queue.put(warning)

    def _format_src_dest(self, fileinfo):
        src = self._format_local_path(fileinfo.src)
        dest = self._format_s3_path(fileinfo.dest)
        return src, dest


class DownloadRequestSubmitter(BaseTransferRequestSubmitter):
    REQUEST_MAPPER_METHOD = RequestParamsMapper.map_get_object_params
    RESULT_SUBSCRIBER_CLASS = DownloadResultSubscriber

    def can_submit(self, fileinfo):
        return fileinfo.operation_name == 'download'

    def _add_additional_subscribers(self, subscribers, fileinfo):
        subscribers.append(ProvideSizeSubscriber(fileinfo.size))
        subscribers.append(ProvideETagSubscriber(fileinfo.etag))
        subscribers.append(DirectoryCreatorSubscriber())
        subscribers.append(ProvideLastModifiedTimeSubscriber(
            fileinfo.last_update, self._result_queue))
        if self._cli_params.get('is_move', False):
            subscribers.append(DeleteSourceObjectSubscriber(
                fileinfo.source_client))
        if fileinfo.case_conflict_submitted is not None:
            subscribers.append(
                CaseConflictCleanupSubscriber(
                    fileinfo.case_conflict_submitted,
                    fileinfo.case_conflict_key,
                )
            )

    def _submit_transfer_request(self, fileinfo, extra_args, subscribers):
        bucket, key = find_bucket_key(fileinfo.src)
        fileout = self._get_fileout(fileinfo)
        return self._transfer_manager.download(
            fileobj=fileout, bucket=bucket, key=key,
            extra_args=extra_args, subscribers=subscribers
        )

    def _get_fileout(self, fileinfo):
        return fileinfo.dest

    def _get_warning_handlers(self):
        return [self._warn_glacier, self._warn_parent_reference]

    def _format_src_dest(self, fileinfo):
        src = self._format_s3_path(fileinfo.src)
        dest = self._format_local_path(fileinfo.dest)
        return src, dest


class CopyRequestSubmitter(BaseTransferRequestSubmitter):
    REQUEST_MAPPER_METHOD = RequestParamsMapper.map_copy_object_params
    RESULT_SUBSCRIBER_CLASS = CopyResultSubscriber

    def can_submit(self, fileinfo):
        return fileinfo.operation_name == 'copy'

    def _add_additional_subscribers(self, subscribers, fileinfo):
        subscribers.append(ProvideSizeSubscriber(fileinfo.size))
        subscribers.append(ProvideETagSubscriber(fileinfo.etag))
        if self._should_inject_content_type():
            subscribers.append(ProvideCopyContentTypeSubscriber())
        if self._cli_params.get('is_move', False):
            subscribers.append(DeleteCopySourceObjectSubscriber(
                fileinfo.source_client))

    def _submit_transfer_request(self, fileinfo, extra_args, subscribers):
        bucket, key = find_bucket_key(fileinfo.dest)
        source_bucket, source_key = find_bucket_key(fileinfo.src)
        copy_source = {'Bucket': source_bucket, 'Key': source_key}
        return self._transfer_manager.copy(
            bucket=bucket, key=key, copy_source=copy_source,
            extra_args=extra_args, subscribers=subscribers,
            source_client=fileinfo.source_client
        )

    def _get_warning_handlers(self):
        return [self._warn_glacier]

    def _format_src_dest(self, fileinfo):
        src = self._format_s3_path(fileinfo.src)
        dest = self._format_s3_path(fileinfo.dest)
        return src, dest


class UploadStreamRequestSubmitter(UploadRequestSubmitter):
    RESULT_SUBSCRIBER_CLASS = UploadStreamResultSubscriber

    def can_submit(self, fileinfo):
        return (
            fileinfo.operation_name == 'upload' and
            self._cli_params.get('is_stream')
        )

    def _add_additional_subscribers(self, subscribers, fileinfo):
        expected_size = self._cli_params.get('expected_size', None)
        if expected_size is not None:
            subscribers.append(ProvideSizeSubscriber(int(expected_size)))

    def _get_filein(self, fileinfo):
        binary_stdin = get_binary_stdin()
        return NonSeekableStream(binary_stdin)

    def _format_local_path(self, path):
        return '-'


class DownloadStreamRequestSubmitter(DownloadRequestSubmitter):
    RESULT_SUBSCRIBER_CLASS = DownloadStreamResultSubscriber

    def can_submit(self, fileinfo):
        return (
            fileinfo.operation_name == 'download' and
            self._cli_params.get('is_stream')
        )

    def _add_additional_subscribers(self, subscribers, fileinfo):
        pass

    def _get_fileout(self, fileinfo):
        return StdoutBytesWriter()

    def _format_local_path(self, path):
        return '-'


class DeleteRequestSubmitter(BaseTransferRequestSubmitter):
    REQUEST_MAPPER_METHOD = RequestParamsMapper.map_delete_object_params
    RESULT_SUBSCRIBER_CLASS = DeleteResultSubscriber

    def can_submit(self, fileinfo):
        return fileinfo.operation_name == 'delete' and \
            fileinfo.src_type == 's3'

    def _submit_transfer_request(self, fileinfo, extra_args, subscribers):
        bucket, key = find_bucket_key(fileinfo.src)
        return self._transfer_manager.delete(
            bucket=bucket, key=key, extra_args=extra_args,
            subscribers=subscribers)

    def _format_src_dest(self, fileinfo):
        return self._format_s3_path(fileinfo.src), None


class LocalDeleteRequestSubmitter(BaseTransferRequestSubmitter):
    REQUEST_MAPPER_METHOD = None
    RESULT_SUBSCRIBER_CLASS = None

    def can_submit(self, fileinfo):
        return fileinfo.operation_name == 'delete' and \
            fileinfo.src_type == 'local'

    def _submit_transfer_request(self, fileinfo, extra_args, subscribers):
        # This is quirky but essentially instead of relying on a built-in
        # method of s3 transfer, the logic lives directly in the submitter.
        # The reason a explicit delete local file does not
        # live in s3transfer is because it is outside the scope of s3transfer;
        # it should only have interfaces for interacting with S3. Therefore,
        # the burden of this functionality should live in the CLI.

        # The main downsides in doing this is that delete and the result
        # creation happens in the main thread as opposed to a separate thread
        # in s3transfer. However, this is not too big of a downside because
        # deleting a local file only happens for sync --delete downloads and
        # is very fast compared to all of the other types of transfers.
        src, dest = self._format_src_dest(fileinfo)
        result_kwargs = {
            'transfer_type': 'delete',
            'src': src,
            'dest': dest
        }
        try:
            self._result_queue.put(QueuedResult(
                total_transfer_size=0, **result_kwargs))
            os.remove(fileinfo.src)
            self._result_queue.put(SuccessResult(**result_kwargs))
        except Exception as e:
            self._result_queue.put(
                FailureResult(exception=e, **result_kwargs))
        finally:
            # Return True to indicate that the transfer was submitted
            return True

    def _format_src_dest(self, fileinfo):
        return self._format_local_path(fileinfo.src), None

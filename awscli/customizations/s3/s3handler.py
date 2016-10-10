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
import math
import os

from s3transfer.manager import TransferManager

from awscli.customizations.s3.utils import (
    find_chunksize, human_readable_size,
    MAX_UPLOAD_SIZE, find_bucket_key, relative_path, PrintTask, create_warning,
    NonSeekableStream)
from awscli.customizations.s3.executor import Executor
from awscli.customizations.s3 import tasks
from awscli.customizations.s3.transferconfig import RuntimeConfig, \
    create_transfer_config_from_runtime_config
from awscli.customizations.s3.results import UploadResultSubscriber
from awscli.customizations.s3.results import DownloadResultSubscriber
from awscli.customizations.s3.results import CopyResultSubscriber
from awscli.customizations.s3.results import UploadStreamResultSubscriber
from awscli.customizations.s3.results import DownloadStreamResultSubscriber
from awscli.customizations.s3.results import DeleteResultSubscriber
from awscli.customizations.s3.results import CommandResult
from awscli.customizations.s3.results import DryRunResult
from awscli.customizations.s3.results import ResultRecorder
from awscli.customizations.s3.results import ResultPrinter
from awscli.customizations.s3.results import OnlyShowErrorsResultPrinter
from awscli.customizations.s3.results import ResultProcessor
from awscli.customizations.s3.results import CommandResultRecorder
from awscli.customizations.s3.utils import RequestParamsMapper
from awscli.customizations.s3.utils import StdoutBytesWriter
from awscli.customizations.s3.utils import ProvideSizeSubscriber
from awscli.customizations.s3.utils import ProvideUploadContentTypeSubscriber
from awscli.customizations.s3.utils import ProvideCopyContentTypeSubscriber
from awscli.customizations.s3.utils import ProvideLastModifiedTimeSubscriber
from awscli.customizations.s3.utils import DirectoryCreatorSubscriber
from awscli.compat import queue
from awscli.compat import binary_stdin


LOGGER = logging.getLogger(__name__)


class BaseS3Handler(object):
    def __init__(self, session, params, result_queue=None,
                 runtime_config=None):
        self.session = session
        if runtime_config is None:
            runtime_config = RuntimeConfig.defaults()
        self._runtime_config = runtime_config
        self.result_queue = result_queue
        if not self.result_queue:
            self.result_queue = queue.Queue()

        self.params = {
            'dryrun': False, 'quiet': False, 'acl': None,
            'guess_mime_type': True, 'sse_c_copy_source': None,
            'sse_c_copy_source_key': None, 'sse': None,
            'sse_c': None, 'sse_c_key': None, 'sse_kms_key_id': None,
            'storage_class': None, 'website_redirect': None,
            'content_type': None, 'cache_control': None,
            'content_disposition': None, 'content_encoding': None,
            'content_language': None, 'expires': None, 'grants': None,
            'only_show_errors': False, 'is_stream': False,
            'paths_type': None, 'expected_size': None, 'metadata': None,
            'metadata_directive': None, 'ignore_glacier_warnings': False,
            'force_glacier_transfer': False
        }
        self.params['region'] = params['region']
        for key in self.params.keys():
            if key in params:
                self.params[key] = params[key]


class S3Handler(BaseS3Handler):
    """
    This class sets up the process to perform the tasks sent to it.  It
    sources the ``self.executor`` from which threads inside the
    class pull tasks from to complete.
    """
    MAX_IO_QUEUE_SIZE = 20

    def __init__(self, session, params, result_queue=None,
                 runtime_config=None):
        super(S3Handler, self).__init__(
            session, params, result_queue, runtime_config)
        # The write_queue has potential for optimizations, so the constant
        # for maxsize is scoped to this class (as opposed to constants.py)
        # so we have the ability to change this value later.
        self.write_queue = queue.Queue(maxsize=self.MAX_IO_QUEUE_SIZE)
        self.multi_threshold = self._runtime_config['multipart_threshold']
        self.chunksize = self._runtime_config['multipart_chunksize']
        LOGGER.debug("Using a multipart threshold of %s and a part size of %s",
                     self.multi_threshold, self.chunksize)
        self.executor = Executor(
            num_threads=self._runtime_config['max_concurrent_requests'],
            result_queue=self.result_queue,
            quiet=self.params['quiet'],
            only_show_errors=self.params['only_show_errors'],
            max_queue_size=self._runtime_config['max_queue_size'],
            write_queue=self.write_queue
        )
        self._multipart_uploads = []
        self._multipart_downloads = []

    def call(self, files):
        """
        This function pulls a ``FileInfo`` or ``TaskInfo`` object from
        a list ``files``.  Each object is then deemed if it will be a
        multipart operation and add the necessary attributes if so.  Each
        object is then wrapped with a ``BasicTask`` object which is
        essentially a thread of execution for a thread to follow.  These
        tasks are then submitted to the main executor.
        """
        try:
            self.executor.start()
            total_files, total_parts = self._enqueue_tasks(files)
            self.executor.print_thread.set_total_files(total_files)
            self.executor.print_thread.set_total_parts(total_parts)
            self.executor.initiate_shutdown()
            self._finalize_shutdown()
        except Exception as e:
            LOGGER.debug('Exception caught during task execution: %s',
                         str(e), exc_info=True)
            self.result_queue.put(PrintTask(message=str(e), error=True))
            self.executor.initiate_shutdown(
                priority=self.executor.IMMEDIATE_PRIORITY)
            self._finalize_shutdown()
        except KeyboardInterrupt:
            self.result_queue.put(PrintTask(message=("Cleaning up. "
                                                     "Please wait..."),
                                            error=True))
            self.executor.initiate_shutdown(
                priority=self.executor.IMMEDIATE_PRIORITY)
            self._finalize_shutdown()
        return CommandResult(self.executor.num_tasks_failed,
                             self.executor.num_tasks_warned)

    def _finalize_shutdown(self):
        # Run all remaining tasks needed to completely shutdown the
        # S3 handler.  This method will block until shutdown is complete.
        # The order here is important.  We need to wait until all the
        # tasks have been completed before we can cleanup.  Otherwise
        # we can have race conditions where we're trying to cleanup
        # uploads/downloads that are still in progress.
        self.executor.wait_until_shutdown()
        self._cleanup()

    def _cleanup(self):
        # And finally we need to make a pass through all the existing
        # multipart uploads and abort any pending multipart uploads.
        self._abort_pending_multipart_uploads()
        self._remove_pending_downloads()

    def _abort_pending_multipart_uploads(self):
        # precondition: this method is assumed to be called when there are no ongoing
        # uploads (the executor has been shutdown).
        for upload, filename in self._multipart_uploads:
            if upload.is_cancelled() or upload.in_progress():
                # Cancel any upload that's not unstarted and not complete.
                upload.cancel_upload(self._cancel_upload, args=(filename,))

    def _remove_pending_downloads(self):
        # The downloads case is easier than the uploads case because we don't
        # need to make any service calls.  To properly cleanup we just need
        # to go through the multipart downloads that were in progress but
        # cancelled and remove the local file.
        for context, local_filename in self._multipart_downloads:
            if (context.is_cancelled() or context.is_started()) and \
                    os.path.exists(local_filename):
                # The file is in an inconsistent state (not all the parts
                # were written to the file) so we should remove the
                # local file rather than leave it in a bad state.  We don't
                # want to remove the files if the download has *not* been
                # started because we haven't touched the file yet, so it's
                # better to leave the old version of the file rather than
                # deleting the file entirely.
                os.remove(local_filename)
            context.cancel()

    def _cancel_upload(self, upload_id, filename):
        bucket, key = find_bucket_key(filename.dest)
        params = {
            'Bucket': bucket,
            'Key': key,
            'UploadId': upload_id,
        }
        LOGGER.debug("Aborting multipart upload for: %s", key)
        filename.client.abort_multipart_upload(**params)

    def _enqueue_tasks(self, files):
        total_files = 0
        total_parts = 0
        for filename in files:
            num_uploads = 1
            is_multipart_task = self._is_multipart_task(filename)
            too_large = False
            if hasattr(filename, 'size'):
                too_large = filename.size > MAX_UPLOAD_SIZE
            if too_large and filename.operation_name == 'upload':
                warning_message = "File exceeds s3 upload limit of 5 TB."
                warning = create_warning(relative_path(filename.src),
                                         warning_message)
                self.result_queue.put(warning)
            # Warn and skip over glacier incompatible tasks.
            elif not self.params.get('force_glacier_transfer') and \
                    not filename.is_glacier_compatible():
                LOGGER.debug(
                    'Encountered glacier object s3://%s. Not performing '
                    '%s on object.' % (filename.src, filename.operation_name))
                if not self.params['ignore_glacier_warnings']:
                    warning = create_warning(
                        's3://'+filename.src,
                        'Object is of storage class GLACIER. Unable to '
                        'perform %s operations on GLACIER objects. You must '
                        'restore the object to be able to the perform '
                        'operation.' %
                        filename.operation_name
                    )
                    self.result_queue.put(warning)
                continue
            elif is_multipart_task and not self.params['dryrun']:
                # If we're in dryrun mode, then we don't need the
                # real multipart tasks.  We can just use a BasicTask
                # in the else clause below, which will print out the
                # fact that it's transferring a file rather than
                # the specific part tasks required to perform the
                # transfer.
                num_uploads = self._enqueue_multipart_tasks(filename)
            else:
                task = tasks.BasicTask(
                    session=self.session, filename=filename,
                    parameters=self.params,
                    result_queue=self.result_queue)
                self.executor.submit(task)
            total_files += 1
            total_parts += num_uploads
        return total_files, total_parts

    def _is_multipart_task(self, filename):
        # First we need to determine if it's an operation that even
        # qualifies for multipart upload.
        if hasattr(filename, 'size'):
            above_multipart_threshold = filename.size > self.multi_threshold
            if above_multipart_threshold:
                if filename.operation_name in ('upload', 'download',
                                               'move', 'copy'):
                    return True
                else:
                    return False
        else:
            return False

    def _enqueue_multipart_tasks(self, filename):
        num_uploads = 1
        if filename.operation_name == 'upload':
            num_uploads = self._enqueue_multipart_upload_tasks(filename)
        elif filename.operation_name == 'move':
            if filename.src_type == 'local' and filename.dest_type == 's3':
                num_uploads = self._enqueue_multipart_upload_tasks(
                    filename, remove_local_file=True)
            elif filename.src_type == 's3' and filename.dest_type == 'local':
                num_uploads = self._enqueue_range_download_tasks(
                    filename, remove_remote_file=True)
            elif filename.src_type == 's3' and filename.dest_type == 's3':
                num_uploads = self._enqueue_multipart_copy_tasks(
                    filename, remove_remote_file=True)
            else:
                raise ValueError("Unknown transfer type of %s -> %s" %
                                 (filename.src_type, filename.dest_type))
        elif filename.operation_name == 'copy':
            num_uploads = self._enqueue_multipart_copy_tasks(
                filename, remove_remote_file=False)
        elif filename.operation_name == 'download':
            num_uploads = self._enqueue_range_download_tasks(filename)
        return num_uploads

    def _enqueue_range_download_tasks(self, filename, remove_remote_file=False):
        num_downloads = int(filename.size / self.chunksize)
        context = tasks.MultipartDownloadContext(num_downloads)
        create_file_task = tasks.CreateLocalFileTask(
            context=context, filename=filename,
            result_queue=self.result_queue)
        self.executor.submit(create_file_task)
        self._do_enqueue_range_download_tasks(
            filename=filename, chunksize=self.chunksize,
            num_downloads=num_downloads, context=context,
            remove_remote_file=remove_remote_file
        )
        complete_file_task = tasks.CompleteDownloadTask(
            context=context, filename=filename, result_queue=self.result_queue,
            params=self.params, io_queue=self.write_queue)
        self.executor.submit(complete_file_task)
        self._multipart_downloads.append((context, filename.dest))
        if remove_remote_file:
            remove_task = tasks.RemoveRemoteObjectTask(
                filename=filename, context=context)
            self.executor.submit(remove_task)
        return num_downloads

    def _do_enqueue_range_download_tasks(self, filename, chunksize,
                                         num_downloads, context,
                                         remove_remote_file=False):
        for i in range(num_downloads):
            task = tasks.DownloadPartTask(
                part_number=i, chunk_size=chunksize,
                result_queue=self.result_queue, filename=filename,
                context=context, io_queue=self.write_queue,
                params=self.params)
            self.executor.submit(task)

    def _enqueue_multipart_upload_tasks(self, filename,
                                        remove_local_file=False):
        # First we need to create a CreateMultipartUpload task,
        # then create UploadTask objects for each of the parts.
        # And finally enqueue a CompleteMultipartUploadTask.
        chunksize = find_chunksize(filename.size, self.chunksize)
        num_uploads = int(math.ceil(filename.size /
                                    float(chunksize)))
        upload_context = self._enqueue_upload_start_task(
            chunksize, num_uploads, filename)
        self._enqueue_upload_tasks(
            num_uploads, chunksize, upload_context, filename, tasks.UploadPartTask)
        self._enqueue_upload_end_task(filename, upload_context)
        if remove_local_file:
            remove_task = tasks.RemoveFileTask(local_filename=filename.src,
                                               upload_context=upload_context)
            self.executor.submit(remove_task)
        return num_uploads

    def _enqueue_multipart_copy_tasks(self, filename,
                                      remove_remote_file=False):
        chunksize = find_chunksize(filename.size, self.chunksize)
        num_uploads = int(math.ceil(filename.size / float(chunksize)))
        upload_context = self._enqueue_upload_start_task(
            chunksize, num_uploads, filename)
        self._enqueue_upload_tasks(
            num_uploads, chunksize, upload_context, filename, tasks.CopyPartTask)
        self._enqueue_upload_end_task(filename, upload_context)
        if remove_remote_file:
            remove_task = tasks.RemoveRemoteObjectTask(
                filename=filename, context=upload_context)
            self.executor.submit(remove_task)
        return num_uploads

    def _enqueue_upload_start_task(self, chunksize, num_uploads, filename):
        upload_context = tasks.MultipartUploadContext(
            expected_parts=num_uploads)
        create_multipart_upload_task = tasks.CreateMultipartUploadTask(
            session=self.session, filename=filename,
            parameters=self.params,
            result_queue=self.result_queue, upload_context=upload_context)
        self.executor.submit(create_multipart_upload_task)
        self._multipart_uploads.append((upload_context, filename))
        return upload_context

    def _enqueue_upload_tasks(self, num_uploads, chunksize, upload_context,
                              filename, task_class):
        for i in range(1, (num_uploads + 1)):
            self._enqueue_upload_single_part_task(
                part_number=i,
                chunk_size=chunksize,
                upload_context=upload_context,
                filename=filename,
                task_class=task_class
            )

    def _enqueue_upload_single_part_task(self, part_number, chunk_size,
                                         upload_context, filename, task_class,
                                         payload=None):
        kwargs = {'part_number': part_number, 'chunk_size': chunk_size,
                  'result_queue': self.result_queue,
                  'upload_context': upload_context, 'filename': filename,
                  'params': self.params}
        if payload:
            kwargs['payload'] = payload
        task = task_class(**kwargs)
        self.executor.submit(task)

    def _enqueue_upload_end_task(self, filename, upload_context):
        complete_multipart_upload_task = tasks.CompleteMultipartUploadTask(
            session=self.session, filename=filename, parameters=self.params,
            result_queue=self.result_queue, upload_context=upload_context)
        self.executor.submit(complete_multipart_upload_task)


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
        subscribers.append(self.RESULT_SUBSCRIBER_CLASS(self._result_queue))
        if not self._cli_params.get('dryrun'):
            return self._submit_transfer_request(
                fileinfo, extra_args, subscribers)
        else:
            self._submit_dryrun(fileinfo)

    def _submit_dryrun(self, fileinfo):
        src, dest = self._format_src_dest(fileinfo)
        self._result_queue.put(DryRunResult(
            transfer_type=fileinfo.operation_name, src=src, dest=dest))

    def _add_additional_subscribers(self, subscribers, fileinfo):
        pass

    def _submit_transfer_request(self, fileinfo, extra_args, subscribers):
        raise NotImplementedError('_submit_transfer_request()')

    def _warn_and_signal_if_skip(self, fileinfo):
        for warning_handler in self._get_warning_handlers():
            if warning_handler(fileinfo):
                # On the first warning handler that returns a signal to skip
                # immediately propogate this signal and no longer check
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
                        'restore the object to be able to the perform '
                        'operation.' %
                        fileinfo.operation_name
                    )
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
        subscribers.append(DirectoryCreatorSubscriber())
        subscribers.append(ProvideLastModifiedTimeSubscriber(
            fileinfo.last_update, self._result_queue))

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
        return [self._warn_glacier]

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
        if self._should_inject_content_type():
            subscribers.append(ProvideCopyContentTypeSubscriber())

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
    REQUEST_MAPPER_METHOD = None
    RESULT_SUBSCRIBER_CLASS = DeleteResultSubscriber

    def can_submit(self, fileinfo):
        return fileinfo.operation_name == 'delete'

    def _submit_transfer_request(self, fileinfo, extra_args, subscribers):
        bucket, key = find_bucket_key(fileinfo.src)
        return self._transfer_manager.delete(
            bucket=bucket, key=key, extra_args=extra_args,
            subscribers=subscribers)

    def _format_src_dest(self, fileinfo):
        return self._format_s3_path(fileinfo.src), None

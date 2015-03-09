import logging
import math
import os
import time
import socket
import threading

from botocore.vendored import requests
from botocore.exceptions import IncompleteReadError
from botocore.vendored.requests.packages.urllib3.exceptions import \
    ReadTimeoutError

from awscli.customizations.s3.utils import find_bucket_key, MD5Error, \
    ReadFileChunk, relative_path, IORequest, IOCloseRequest, PrintTask


LOGGER = logging.getLogger(__name__)


class UploadCancelledError(Exception):
    pass


class DownloadCancelledError(Exception):
    pass


class RetriesExeededError(Exception):
    pass


def print_operation(filename, failed, dryrun=False):
    """
    Helper function used to print out what an operation did and whether
    it failed.
    """
    print_str = filename.operation_name
    if dryrun:
        print_str = '(dryrun) ' + print_str
    if failed:
        print_str += " failed"
    print_str += ": "
    if filename.src_type == "s3":
        print_str = print_str + "s3://" + filename.src
    else:
        print_str += relative_path(filename.src)
    if filename.operation_name not in ["delete", "make_bucket",
                                       "remove_bucket"]:
        if filename.dest_type == "s3":
            print_str += " to s3://" + filename.dest
        else:
            print_str += " to " + relative_path(filename.dest)
    return print_str


class OrderableTask(object):
    PRIORITY = 10


class BasicTask(OrderableTask):
    """
    This class is a wrapper for all ``TaskInfo`` and ``TaskInfo`` objects
    It is practically a thread of execution.  It also injects the necessary
    attributes like ``session`` object in order for the filename to
    perform its designated operation.
    """
    def __init__(self, session, filename, parameters,
                 result_queue, payload=None):
        self.session = session

        self.filename = filename
        self.filename.parameters = parameters

        self.parameters = parameters
        self.result_queue = result_queue
        self.payload = payload

    def __call__(self):
        self._execute_task(attempts=3)

    def _execute_task(self, attempts, last_error=''):
        if attempts == 0:
            # We've run out of retries.
            self._queue_print_message(self.filename, failed=True,
                                      dryrun=self.parameters['dryrun'],
                                      error_message=last_error)
            return
        filename = self.filename
        kwargs = {}
        if self.payload:
            kwargs['payload'] = self.payload
        try:
            if not self.parameters['dryrun']:
                getattr(filename, filename.operation_name)(**kwargs)
        except requests.ConnectionError as e:
            connect_error = str(e)
            LOGGER.debug("%s %s failure: %s",
                         filename.src, filename.operation_name, connect_error)
            self._execute_task(attempts - 1, last_error=str(e))
        except MD5Error as e:
            LOGGER.debug("%s %s failure: Data was corrupted: %s",
                         filename.src, filename.operation_name, e)
            self._execute_task(attempts - 1, last_error=str(e))
        except Exception as e:
            LOGGER.debug(str(e), exc_info=True)
            self._queue_print_message(filename, failed=True,
                                      dryrun=self.parameters['dryrun'],
                                      error_message=str(e))
        else:
            self._queue_print_message(filename, failed=False,
                                      dryrun=self.parameters['dryrun'])

    def _queue_print_message(self, filename, failed, dryrun,
                             error_message=None):
        try:
            if filename.operation_name != 'list_objects':
                message = print_operation(filename, failed,
                                          self.parameters['dryrun'])
                if error_message is not None:
                    message += ' ' + error_message
                result = {'message': message, 'error': failed}
                self.result_queue.put(PrintTask(**result))
        except Exception as e:
            LOGGER.debug('%s' % str(e))


class CopyPartTask(OrderableTask):
    def __init__(self, part_number, chunk_size,
                 result_queue, upload_context, filename):
        self._result_queue = result_queue
        self._upload_context = upload_context
        self._part_number = part_number
        self._chunk_size = chunk_size
        self._filename = filename

    def _is_last_part(self, part_number):
        return self._part_number == int(
            math.ceil(self._filename.size / float(self._chunk_size)))

    def _total_parts(self):
        return int(math.ceil(
            self._filename.size / float(self._chunk_size)))

    def __call__(self):
        LOGGER.debug("Uploading part copy %s for filename: %s",
                     self._part_number, self._filename.src)
        total_file_size = self._filename.size
        start_range = (self._part_number - 1) * self._chunk_size
        if self._is_last_part(self._part_number):
            end_range = total_file_size - 1
        else:
            end_range = start_range + self._chunk_size - 1
        range_param = 'bytes=%s-%s' % (start_range, end_range)
        try:
            LOGGER.debug("Waiting for upload id.")
            upload_id = self._upload_context.wait_for_upload_id()
            bucket, key = find_bucket_key(self._filename.dest)
            src_bucket, src_key = find_bucket_key(self._filename.src)
            params = {'Bucket': bucket, 'Key': key,
                      'PartNumber': self._part_number,
                      'UploadId': upload_id,
                      'CopySource': '%s/%s' % (src_bucket, src_key),
                      'CopySourceRange': range_param}
            response_data = self._filename.client.upload_part_copy(**params)
            etag = response_data['CopyPartResult']['ETag'][1:-1]
            self._upload_context.announce_finished_part(
                etag=etag, part_number=self._part_number)

            message = print_operation(self._filename, 0)
            result = {'message': message, 'total_parts': self._total_parts(),
                      'error': False}
            self._result_queue.put(PrintTask(**result))
        except UploadCancelledError as e:
            # We don't need to do anything in this case.  The task
            # has been cancelled, and the task that cancelled the
            # task has already queued a message.
            LOGGER.debug("Not uploading part copy, task has been cancelled.")
        except Exception as e:
            LOGGER.debug('Error during upload part copy: %s', e,
                         exc_info=True)
            message = print_operation(self._filename, failed=True,
                                      dryrun=False)
            message += '\n' + str(e)
            result = {'message': message, 'error': True}
            self._result_queue.put(PrintTask(**result))
            self._upload_context.cancel_upload()
        else:
            LOGGER.debug("Copy part number %s completed for filename: %s",
                         self._part_number, self._filename.src)


class UploadPartTask(OrderableTask):
    """
    This is a task used to upload a part of a multipart upload.
    This task pulls from a ``part_queue`` which represents the
    queue for a specific multipart upload.  This pulling from a
    ``part_queue`` is necessary in order to keep track and
    complete the multipart upload initiated by the ``FileInfo``
    object.
    """
    def __init__(self, part_number, chunk_size, result_queue, upload_context,
                 filename, payload=None):
        self._result_queue = result_queue
        self._upload_context = upload_context
        self._part_number = part_number
        self._chunk_size = chunk_size
        self._filename = filename
        self._payload = payload

    def _read_part(self):
        actual_filename = self._filename.src
        in_file_part_number = self._part_number - 1
        starting_byte = in_file_part_number * self._chunk_size
        return ReadFileChunk(actual_filename, starting_byte, self._chunk_size)

    def __call__(self):
        LOGGER.debug("Uploading part %s for filename: %s",
                     self._part_number, self._filename.src)
        try:
            LOGGER.debug("Waiting for upload id.")
            upload_id = self._upload_context.wait_for_upload_id()
            bucket, key = find_bucket_key(self._filename.dest)
            if self._filename.is_stream:
                body = self._payload
                total = self._upload_context.expected_parts
            else:
                total = int(math.ceil(
                    self._filename.size/float(self._chunk_size)))
                body = self._read_part()
            params = {'Bucket': bucket, 'Key': key,
                      'PartNumber': self._part_number,
                      'UploadId': upload_id,
                      'Body': body}
            try:
                response_data = self._filename.client.upload_part(**params)
            finally:
                body.close()
            etag = response_data['ETag'][1:-1]
            self._upload_context.announce_finished_part(
                etag=etag, part_number=self._part_number)

            message = print_operation(self._filename, 0)
            result = {'message': message, 'total_parts': total,
                      'error': False}
            self._result_queue.put(PrintTask(**result))
        except UploadCancelledError as e:
            # We don't need to do anything in this case.  The task
            # has been cancelled, and the task that cancelled the
            # task has already queued a message.
            LOGGER.debug("Not uploading part, task has been cancelled.")
        except Exception as e:
            LOGGER.debug('Error during part upload: %s', e,
                         exc_info=True)
            message = print_operation(self._filename, failed=True,
                                      dryrun=False)
            message += '\n' + str(e)
            result = {'message': message, 'error': True}
            self._result_queue.put(PrintTask(**result))
            self._upload_context.cancel_upload()
        else:
            LOGGER.debug("Part number %s completed for filename: %s",
                         self._part_number, self._filename.src)


class CreateLocalFileTask(OrderableTask):
    def __init__(self, context, filename):
        self._context = context
        self._filename = filename

    def __call__(self):
        dirname = os.path.dirname(self._filename.dest)
        try:
            if not os.path.isdir(dirname):
                try:
                    os.makedirs(dirname)
                except OSError:
                    # It's possible that between the if check and the makedirs
                    # check that another thread has come along and created the
                    # directory.  In this case the directory already exists and we
                    # can move on.
                    pass
            # Always create the file.  Even if it exists, we need to
            # wipe out the existing contents.
            with open(self._filename.dest, 'wb'):
                pass
        except Exception as e:
            self._context.cancel()
        else:
            self._context.announce_file_created()


class CompleteDownloadTask(OrderableTask):
    def __init__(self, context, filename, result_queue, params, io_queue):
        self._context = context
        self._filename = filename
        self._result_queue = result_queue
        self._parameters = params
        self._io_queue = io_queue

    def __call__(self):
        # When the file is downloading, we have a few things we need to do:
        # 1) Fix up the last modified time to match s3.
        # 2) Tell the result_queue we're done.
        # 3) Queue an IO request to the IO thread letting it know we're
        #    done with the file.
        self._context.wait_for_completion()
        last_update_tuple = self._filename.last_update.timetuple()
        mod_timestamp = time.mktime(last_update_tuple)
        desired_mtime = int(mod_timestamp)
        message = print_operation(self._filename, False,
                                  self._parameters['dryrun'])
        print_task = {'message': message, 'error': False}
        self._result_queue.put(PrintTask(**print_task))
        self._io_queue.put(IOCloseRequest(self._filename.dest, desired_mtime))


class DownloadPartTask(OrderableTask):
    """
    This task downloads and writes a part to a file.  This task pulls
    from a ``part_queue`` which represents the queue for a specific
    multipart download.  This pulling from a ``part_queue`` is necessary
    in order to keep track and complete the multipart download initiated by
    the ``FileInfo`` object.
    """

    # Amount to read from response body at a time.
    ITERATE_CHUNK_SIZE = 1024 * 1024
    READ_TIMEOUT = 60
    TOTAL_ATTEMPTS = 5

    def __init__(self, part_number, chunk_size, result_queue,
                 filename, context, io_queue):
        self._part_number = part_number
        self._chunk_size = chunk_size
        self._result_queue = result_queue
        self._filename = filename
        self._client = filename.client
        self._context = context
        self._io_queue = io_queue

    def __call__(self):
        try:
            self._download_part()
        except Exception as e:
            LOGGER.debug(
                'Exception caught downloading byte range: %s',
                e, exc_info=True)
            self._context.cancel()
            raise e

    def _download_part(self):
        total_file_size = self._filename.size
        start_range = self._part_number * self._chunk_size
        if self._part_number == int(total_file_size / self._chunk_size) - 1:
            end_range = ''
        else:
            end_range = start_range + self._chunk_size - 1
        range_param = 'bytes=%s-%s' % (start_range, end_range)
        LOGGER.debug("Downloading bytes range of %s for file %s", range_param,
                     self._filename.dest)
        bucket, key = find_bucket_key(self._filename.src)
        params = {'Bucket': bucket, 'Key': key, 'Range': range_param}
        for i in range(self.TOTAL_ATTEMPTS):
            try:
                LOGGER.debug("Making GetObject requests with byte range: %s",
                             range_param)
                response_data = self._client.get_object(**params)
                LOGGER.debug("Response received from GetObject")
                body = response_data['Body']
                self._queue_writes(body)
                self._context.announce_completed_part(self._part_number)

                message = print_operation(self._filename, 0)
                total_parts = int(self._filename.size / self._chunk_size)
                result = {'message': message, 'error': False,
                          'total_parts': total_parts}
                self._result_queue.put(PrintTask(**result))
                LOGGER.debug("Task complete: %s", self)
                return
            except (socket.timeout, socket.error, ReadTimeoutError) as e:
                LOGGER.debug("Timeout error caught, retrying request, "
                             "(attempt %s / %s)", i, self.TOTAL_ATTEMPTS,
                             exc_info=True)
                continue
            except IncompleteReadError as e:
                LOGGER.debug("Incomplete read detected: %s, (attempt %s / %s)",
                             e, i, self.TOTAL_ATTEMPTS)
                continue
        raise RetriesExeededError("Maximum number of attempts exceeded: %s" %
                                  self.TOTAL_ATTEMPTS)

    def _queue_writes(self, body):
        self._context.wait_for_file_created()
        LOGGER.debug("Writing part number %s to file: %s",
                     self._part_number, self._filename.dest)
        iterate_chunk_size = self.ITERATE_CHUNK_SIZE
        body.set_socket_timeout(self.READ_TIMEOUT)
        if self._filename.is_stream:
            self._queue_writes_for_stream(body)
        else:
            self._queue_writes_in_chunks(body, iterate_chunk_size)

    def _queue_writes_for_stream(self, body):
        # We have to handle an output stream differently.  The main reason is
        # that we cannot seek() in the output stream.  This means that we need
        # to queue the writes in order.  If we queue IO writes in smaller than
        # part size chunks, on the case of a retry we'll need to do a range GET
        # for only the remaining parts.  The other alternative, which is what
        # we do here, is to just request the entire chunk size write.
        self._context.wait_for_turn(self._part_number)
        chunk = body.read()
        offset = self._part_number * self._chunk_size
        LOGGER.debug("Submitting IORequest to write queue.")
        self._io_queue.put(
            IORequest(self._filename.dest, offset, chunk,
                      self._filename.is_stream)
        )
        self._context.done_with_turn()

    def _queue_writes_in_chunks(self, body, iterate_chunk_size):
        amount_read = 0
        current = body.read(iterate_chunk_size)
        while current:
            offset = self._part_number * self._chunk_size + amount_read
            LOGGER.debug("Submitting IORequest to write queue.")
            self._io_queue.put(
                IORequest(self._filename.dest, offset, current,
                          self._filename.is_stream)
            )
            LOGGER.debug("Request successfully submitted.")
            amount_read += len(current)
            current = body.read(iterate_chunk_size)
        # Change log message.
        LOGGER.debug("Done queueing writes for part number %s to file: %s",
                     self._part_number, self._filename.dest)


class CreateMultipartUploadTask(BasicTask):
    def __init__(self, session, filename, parameters, result_queue,
                 upload_context):
        super(CreateMultipartUploadTask, self).__init__(
            session, filename, parameters, result_queue)
        self._upload_context = upload_context

    def __call__(self):
        LOGGER.debug("Creating multipart upload for file: %s",
                     self.filename.src)
        try:
            upload_id = self.filename.create_multipart_upload()
            LOGGER.debug("Announcing upload id: %s", upload_id)
            self._upload_context.announce_upload_id(upload_id)
        except Exception as e:
            LOGGER.debug("Error trying to create multipart upload: %s",
                         e, exc_info=True)
            self._upload_context.cancel_upload()
            message = print_operation(self.filename, True,
                                      self.parameters['dryrun'])
            message += '\n' + str(e)
            result = {'message': message, 'error': True}
            self.result_queue.put(PrintTask(**result))
            raise e


class RemoveRemoteObjectTask(OrderableTask):
    def __init__(self, filename, context):
        self._context = context
        self._filename = filename

    def __call__(self):
        LOGGER.debug("Waiting for download to finish.")
        self._context.wait_for_completion()
        bucket, key = find_bucket_key(self._filename.src)
        params = {'Bucket': bucket, 'Key': key}
        self._filename.source_client.delete_object(**params)


class CompleteMultipartUploadTask(BasicTask):
    def __init__(self, session, filename, parameters, result_queue,
                 upload_context):
        super(CompleteMultipartUploadTask, self).__init__(
            session, filename, parameters, result_queue)
        self._upload_context = upload_context

    def __call__(self):
        LOGGER.debug("Completing multipart upload for file: %s",
                     self.filename.src)
        upload_id = self._upload_context.wait_for_upload_id()
        parts = self._upload_context.wait_for_parts_to_finish()
        LOGGER.debug("Received upload id and parts list.")
        bucket, key = find_bucket_key(self.filename.dest)
        params = {
            'Bucket': bucket, 'Key': key,
            'UploadId': upload_id,
            'MultipartUpload': {'Parts': parts},
        }
        try:
            self.filename.client.complete_multipart_upload(**params)
        except Exception as e:
            LOGGER.debug("Error trying to complete multipart upload: %s",
                         e, exc_info=True)
            message = print_operation(
                self.filename, failed=True,
                dryrun=self.parameters['dryrun'])
            message += '\n' + str(e)
            result = {
                'message': message,
                'error': True
            }
        else:
            LOGGER.debug("Multipart upload completed for: %s",
                         self.filename.src)
            message = print_operation(self.filename, False,
                                      self.parameters['dryrun'])
            result = {'message': message, 'error': False}
            self._upload_context.announce_completed()
        self.result_queue.put(PrintTask(**result))


class RemoveFileTask(BasicTask):
    def __init__(self, local_filename, upload_context):
        self._local_filename = local_filename
        self._upload_context = upload_context
        # This 'filename' attr has to be here because other objects
        # introspect tasks objects.  This should eventually be removed
        # but it's needed for now.
        self.filename = None

    def __call__(self):
        LOGGER.debug("Waiting for upload to complete.")
        self._upload_context.wait_for_completion()
        LOGGER.debug("Removing local file: %s", self._local_filename)
        os.remove(self._local_filename)


class MultipartUploadContext(object):
    """Context object for a multipart upload.

    Performing a multipart upload usually consists of three parts:

        * CreateMultipartUpload
        * UploadPart
        * CompleteMultipartUpload

    Each of those three parts are not independent of each other.  In order
    to upload a part, you need to know the upload id (created during the
    CreateMultipartUpload operation).  In order to complete a multipart
    you need the etags from all the parts (created during the UploadPart
    operations).  This context object provides the necessary building blocks
    to allow for the three stages to efficiently communicate with each other.

    This class is thread safe.

    """
    # These are the valid states for this object.
    _UNSTARTED = '_UNSTARTED'
    _STARTED = '_STARTED'
    _CANCELLED = '_CANCELLED'
    _COMPLETED = '_COMPLETED'

    def __init__(self, expected_parts='...'):
        self._upload_id = None
        self._expected_parts = expected_parts
        self._parts = []
        self._lock = threading.Lock()
        self._upload_id_condition = threading.Condition(self._lock)
        self._parts_condition = threading.Condition(self._lock)
        self._upload_complete_condition = threading.Condition(self._lock)
        self._state = self._UNSTARTED

    @property
    def expected_parts(self):
        return self._expected_parts

    def announce_upload_id(self, upload_id):
        with self._upload_id_condition:
            self._upload_id = upload_id
            self._state = self._STARTED
            self._upload_id_condition.notifyAll()

    def announce_finished_part(self, etag, part_number):
        with self._parts_condition:
            self._parts.append({'ETag': etag, 'PartNumber': part_number})
            self._parts_condition.notifyAll()

    def announce_total_parts(self, total_parts):
        with self._parts_condition:
            self._expected_parts = total_parts
            self._parts_condition.notifyAll()

    def wait_for_parts_to_finish(self):
        with self._parts_condition:
            while self._expected_parts == '...' or \
                    len(self._parts) < self._expected_parts:
                if self._state == self._CANCELLED:
                    raise UploadCancelledError("Upload has been cancelled.")
                self._parts_condition.wait(timeout=1)
            return list(sorted(self._parts, key=lambda p: p['PartNumber']))

    def wait_for_upload_id(self):
        with self._upload_id_condition:
            while self._upload_id is None and self._state != self._CANCELLED:
               self._upload_id_condition.wait(timeout=1)
            if self._state == self._CANCELLED:
               raise UploadCancelledError("Upload has been cancelled.")
            return self._upload_id

    def wait_for_completion(self):
        with self._upload_complete_condition:
            while not self._state == self._COMPLETED:
                if self._state == self._CANCELLED:
                    raise UploadCancelledError("Upload has been cancelled.")
                self._upload_complete_condition.wait(timeout=1)

    def cancel_upload(self, canceller=None, args=None, kwargs=None):
        """Cancel the upload.

        If the upload is already in progress (via ``self.in_progress()``)
        you can provide a ``canceller`` argument that can be used to cancel
        the multipart upload request (typically this would call something like
        AbortMultipartUpload.  The canceller argument is a function that takes
        a single argument, which is the upload id::

            def my_canceller(upload_id):
                cancel.upload(bucket, key, upload_id)

        The ``canceller`` callable will only be called if the
        task is in progress.  If the task has not been started or is
        complete, then ``canceller`` will not be called.

        Note that ``canceller`` is called while an exclusive lock is held,
        so you cannot make any calls into the MultipartUploadContext object
        in the ``canceller`` object.

        """
        with self._lock:
            if self._state == self._STARTED and canceller is not None:
                if args is None:
                    args = ()
                if kwargs is None:
                    kwargs = {}
                canceller(self._upload_id, *args, **kwargs)
            self._state = self._CANCELLED

    def in_progress(self):
        """Determines whether or not the multipart upload is in process.

        Note that this has a very short gap from the time that a
        CreateMultipartUpload is called to the time the
        MultipartUploadContext object is told about the upload
        where this method will return False even though the multipart
        upload is in fact in progress.  This is solely based on whether
        or not the MultipartUploadContext has been notified about an
        upload id.
        """
        with self._lock:
            return self._state == self._STARTED

    def is_complete(self):
        with self._lock:
            return self._state == self._COMPLETED

    def is_cancelled(self):
        with self._lock:
            return self._state == self._CANCELLED

    def announce_completed(self):
        """Let the context object know that the upload is complete.

        This should be called after a CompleteMultipartUpload operation.

        """
        with self._upload_complete_condition:
            self._state = self._COMPLETED
            self._upload_complete_condition.notifyAll()


class MultipartDownloadContext(object):

    _STATES = {
        'UNSTARTED': 'UNSTARTED',
        'STARTED': 'STARTED',
        'COMPLETED': 'COMPLETED',
        'CANCELLED': 'CANCELLED'
    }

    def __init__(self, num_parts, lock=None):
        self.num_parts = num_parts

        if lock is None:
            lock = threading.Lock()
        self._lock = lock
        self._created_condition = threading.Condition(self._lock)
        self._submit_write_condition = threading.Condition(self._lock)
        self._completed_condition = threading.Condition(self._lock)
        self._state = self._STATES['UNSTARTED']
        self._finished_parts = set()
        self._current_stream_part_number = 0

    def announce_completed_part(self, part_number):
        with self._completed_condition:
            self._finished_parts.add(part_number)
            if len(self._finished_parts) == self.num_parts:
                self._state = self._STATES['COMPLETED']
                self._completed_condition.notifyAll()

    def announce_file_created(self):
        with self._created_condition:
            self._state = self._STATES['STARTED']
            self._created_condition.notifyAll()

    def wait_for_file_created(self):
        with self._created_condition:
            while not self._state == self._STATES['STARTED']:
                if self._state == self._STATES['CANCELLED']:
                    raise DownloadCancelledError(
                        "Download has been cancelled.")
                self._created_condition.wait(timeout=1)

    def wait_for_completion(self):
        with self._completed_condition:
            while not self._state == self._STATES['COMPLETED']:
                if self._state == self._STATES['CANCELLED']:
                    raise DownloadCancelledError(
                        "Download has been cancelled.")
                self._completed_condition.wait(timeout=1)

    def wait_for_turn(self, part_number):
        with self._submit_write_condition:
            while self._current_stream_part_number != part_number:
                if self._state == self._STATES['CANCELLED']:
                    raise DownloadCancelledError(
                        "Download has been cancelled.")
                self._submit_write_condition.wait(timeout=0.2)

    def done_with_turn(self):
        with self._submit_write_condition:
            self._current_stream_part_number += 1
            self._submit_write_condition.notifyAll()

    def cancel(self):
        with self._lock:
            self._state = self._STATES['CANCELLED']

    def is_cancelled(self):
        with self._lock:
            return self._state == self._STATES['CANCELLED']

    def is_started(self):
        with self._lock:
            return self._state == self._STATES['STARTED']

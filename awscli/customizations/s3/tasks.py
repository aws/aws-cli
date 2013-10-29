import logging
import math
import os
import time
import threading

from botocore.vendored import requests

from awscli.customizations.s3.utils import find_bucket_key, MD5Error, \
    operate, ReadFileChunk, relative_path


LOGGER = logging.getLogger(__name__)


class UploadCancelledError(Exception):
    pass


class DownloadCancelledError(Exception):
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
    if filename.operation_name not in ["delete", "make_bucket", "remove_bucket"]:
        if filename.dest_type == "s3":
            print_str += " to s3://" + filename.dest
        else:
            print_str += " to " + relative_path(filename.dest)
    return print_str


class BasicTask(object):
    """
    This class is a wrapper for all ``TaskInfo`` and ``TaskInfo`` objects
    It is practically a thread of execution.  It also injects the necessary
    attributes like ``session`` object in order for the filename to
    perform its designated operation.
    """
    def __init__(self, session, filename, parameters, result_queue):
        self.session = session
        self.service = self.session.get_service('s3')

        self.filename = filename
        self.filename.parameters = parameters

        self.parameters = parameters
        self.result_queue = result_queue

    def __call__(self):
        self._execute_task(attempts=3)

    def _execute_task(self, attempts, last_error=''):
        if attempts == 0:
            # We've run out of retries.
            self._queue_print_message(self.filename, failed=True,
                                      dryrun=self.parameters['dryrun'],
                                      error_message=last_error)
        filename = self.filename
        try:
            if not self.parameters['dryrun']:
                getattr(filename, filename.operation_name)()
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
                    message += '\n' + error_message
                result = {'message': message, 'error': failed}
                self.result_queue.put(result)
        except Exception as e:
            LOGGER.debug('%s' % str(e))


class UploadPartTask(object):
    """
    This is a task used to upload a part of a multipart upload.
    This task pulls from a ``part_queue`` which represents the
    queue for a specific multipart upload.  This pulling from a
    ``part_queue`` is necessary in order to keep track and
    complete the multipart upload initiated by the ``FileInfo``
    object.
    """
    def __init__(self, part_number, chunk_size,
                 result_queue, upload_context, filename):
        self._result_queue = result_queue
        self._upload_context = upload_context
        self._part_number = part_number
        self._chunk_size = chunk_size
        self._filename = filename

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
            total = int(math.ceil(
                self._filename.size/float(self._chunk_size)))
            body = self._read_part()
            params = {'endpoint': self._filename.endpoint,
                      'bucket': bucket, 'key': key,
                      'part_number': str(self._part_number),
                      'upload_id': upload_id,
                      'body': body}
            try:
                response_data, http = operate(
                    self._filename.service, 'UploadPart', params)
            finally:
                body.close()
            etag = response_data['ETag'][1:-1]
            self._upload_context.announce_finished_part(
                etag=etag, part_number=self._part_number)

            message = print_operation(self._filename, 0)
            result = {'message': message, 'total_parts': total,
                      'error': False}
            self._result_queue.put(result)
        except UploadCancelledError as e:
            # We don't need to do anything in this case.  The task
            # has been cancelled, and the task that cancelled the
            # task has already queued a message.
            LOGGER.debug("Not uploading part, task has been cancelled.")
        except Exception as e:
            LOGGER.debug('Error during part upload: %s' , e,
                         exc_info=True)
            message = print_operation(self._filename, failed=True,
                                      dryrun=False)
            message += '\n' + str(e)
            result = {'message': message, 'error': True}
            self._result_queue.put(result)
            self._upload_context.cancel_upload()
        else:
            LOGGER.debug("Part number %s completed for filename: %s",
                     self._part_number, self._filename.src)


class CreateLocalFileTask(object):
    def __init__(self, context, filename):
        self._context = context
        self._filename = filename

    def __call__(self):
        dirname = os.path.dirname(self._filename.dest)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        # Always create the file.  Even if it exists, we need to
        # wipe out the existing contents.
        with open(self._filename.dest, 'wb'):
            pass
        self._context.announce_file_created()


class CompleteDownloadTask(object):
    def __init__(self, context, filename, result_queue, params):
        self._context = context
        self._filename = filename
        self._result_queue = result_queue
        self._parameters = params

    def __call__(self):
        # When the file is downloading, we have a few things we need to do:
        # 1) Fix up the last modified time to match s3.
        # 2) Tell the result_queue we're done.
        self._context.wait_for_completion()
        last_update_tuple = self._filename.last_update.timetuple()
        mod_timestamp = time.mktime(last_update_tuple)
        os.utime(self._filename.dest, (int(mod_timestamp), int(mod_timestamp)))
        message = print_operation(self._filename, False,
                                  self._parameters['dryrun'])
        print_task = {'message': message, 'error': False}
        self._result_queue.put(print_task)


class DownloadPartTask(object):
    """
    This task downloads and writes a part to a file.  This task pulls
    from a ``part_queue`` which represents the queue for a specific
    multipart download.  This pulling from a ``part_queue`` is necessary
    in order to keep track and complete the multipart download initiated by
    the ``FileInfo`` object.
    """

    # Amount to read from response body at a time.
    ITERATE_CHUNK_SIZE = 1024 * 1024

    def __init__(self, part_number, chunk_size, result_queue, service,
                 filename, context):
        self._part_number = part_number
        self._chunk_size = chunk_size
        self._result_queue = result_queue
        self._filename = filename
        self._service = filename.service
        self._context = context

    def __call__(self):
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
        params = {'endpoint': self._filename.endpoint, 'bucket': bucket,
                  'key': key, 'range': range_param}
        try:
            LOGGER.debug("Making GetObject requests with byte range: %s",
                         range_param)
            response_data, http = operate(self._service, 'GetObject',
                                          params)
            LOGGER.debug("Response received from GetObject")
            body = response_data['Body']
            self._write_to_file(body)
            self._context.announce_completed_part(self._part_number)

            message = print_operation(self._filename, 0)
            total_parts = int(self._filename.size / self._chunk_size)
            result = {'message': message, 'error': False,
                      'total_parts': total_parts}
            self._result_queue.put(result)
        except Exception as e:
            LOGGER.debug(
                'Exception caught downloading byte range: %s',
                e, exc_info=True)
            self._context.cancel()
            raise e

    def _write_to_file(self, body):
        self._context.wait_for_file_created()
        LOGGER.debug("Writing part number %s to file: %s",
                     self._part_number, self._filename.dest)
        iterate_chunk_size = self.ITERATE_CHUNK_SIZE
        with open(self._filename.dest, 'rb+') as f:
            f.seek(self._part_number * self._chunk_size)
            current = body.read(iterate_chunk_size)
            while current:
                f.write(current)
                current = body.read(iterate_chunk_size)
        LOGGER.debug("Done writing part number %s to file: %s",
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
            self.result_queue.put(result)
            raise e


class RemoveRemoteObjectTask(object):
    def __init__(self, filename, context):
        self._context = context
        self._filename = filename

    def __call__(self):
        LOGGER.debug("Waiting for download to finish.")
        self._context.wait_for_completion()
        bucket, key = find_bucket_key(self._filename.src)
        params = {'endpoint': self._filename.endpoint,
                  'bucket': bucket, 'key': key}
        response_data, http = operate(
            self._filename.service, 'DeleteObject', params)


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
            'bucket': bucket, 'key': key,
            'endpoint': self.filename.endpoint,
            'upload_id': upload_id,
            'multipart_upload': {'Parts': parts},
        }
        try:
            operate(self.filename.service, 'CompleteMultipartUpload', params)
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
        self.result_queue.put(result)


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

    def __init__(self, expected_parts):
        self._upload_id = None
        self._expected_parts = expected_parts
        self._parts = []
        self._lock = threading.Lock()
        self._upload_id_condition = threading.Condition(self._lock)
        self._parts_condition = threading.Condition(self._lock)
        self._upload_complete_condition = threading.Condition(self._lock)
        self._state = self._UNSTARTED

    def announce_upload_id(self, upload_id):
        with self._upload_id_condition:
            self._upload_id = upload_id
            self._state = self._STARTED
            self._upload_id_condition.notifyAll()

    def announce_finished_part(self, etag, part_number):
        with self._parts_condition:
            self._parts.append({'ETag': etag, 'PartNumber': part_number})
            self._parts_condition.notifyAll()

    def wait_for_parts_to_finish(self):
        with self._parts_condition:
            while len(self._parts) < self._expected_parts:
                if self._state == self._CANCELLED:
                    raise UploadCancelledError("Upload has been cancelled.")
                self._parts_condition.wait(timeout=1)
            return list(sorted(self._parts, key=lambda p: p['PartNumber']))

    def wait_for_upload_id(self):
        with self._upload_id_condition:
            while self._upload_id is None:
                if self._state == self._CANCELLED:
                    raise UploadCancelledError("Upload has been cancelled.")
                self._upload_id_condition.wait(timeout=1)
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
        'CANCELLED':'CANCELLED'
    }

    def __init__(self, num_parts, lock=None):
        self.num_parts = num_parts

        if lock is None:
            lock = threading.Lock()
        self._lock = lock
        self._created_condition = threading.Condition(self._lock)
        self._completed_condition = threading.Condition(self._lock)
        self._state = self._STATES['UNSTARTED']
        self._finished_parts = set()

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
                    raise DownloadCancelledError("Download has been cancelled.")
                self._created_condition.wait(timeout=1)

    def wait_for_completion(self):
        with self._completed_condition:
            while not self._state == self._STATES['COMPLETED']:
                if self._state == self._STATES['CANCELLED']:
                    raise DownloadCancelledError("Download has been cancelled.")
                self._completed_condition.wait(timeout=1)

    def cancel(self):
        with self._lock:
            self._state = self._STATES['CANCELLED']

    def is_cancelled(self):
        with self._lock:
            return self._state == self._STATES['CANCELLED']

    def is_started(self):
        with self._lock:
            return self._state == self._STATES['STARTED']

import logging
import math
import os
import requests
from six import StringIO
from six.moves import queue as Queue
import sys
import threading

from awscli.customizations.s3.constants import QUEUE_TIMEOUT_GET
from awscli.customizations.s3.utils import find_bucket_key, MD5Error, \
    operate, retrieve_http_etag

LOGGER = logging.getLogger(__name__)


class UploadCancelledError(Exception):
    pass


def print_operation(filename, failed, dryrun=False):
    """
    Helper function used to print out what an operation did and whether
    it failed.
    """
    print_str = filename.operation
    if dryrun:
        print_str = '(dryrun) ' + print_str
    if failed:
        print_str += " failed"
    print_str += ": "
    if filename.src_type == "s3":
        print_str = print_str + "s3://" + filename.src
    else:
        print_str += os.path.relpath(filename.src)
    if filename.operation not in ["delete", "make_bucket", "remove_bucket"]:
        if filename.dest_type == "s3":
            print_str += " to s3://" + filename.dest
        else:
            print_str += " to " + os.path.relpath(filename.dest)
    return print_str


class BasicTask(object):
    """
    This class is a wrapper for all ``TaskInfo`` and ``TaskInfo`` objects
    It is practically a thread of execution.  It also injects the necessary
    attributes like ``session`` object in order for the filename to
    perform its designated operation.
    """
    def __init__(self, session, filename, parameters, print_queue):
        self.session = session
        self.service = self.session.get_service('s3')

        self.filename = filename
        self.filename.parameters = parameters

        self.parameters = parameters
        self.print_queue = print_queue

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
                getattr(filename, filename.operation)()
        except requests.ConnectionError as e:
            connect_error = str(e)
            LOGGER.debug("%s %s failure: %s",
                         filename.src, filename.operation, connect_error)
            self._execute_task(attempts - 1, last_error=str(e))
        except MD5Error as e:
            LOGGER.debug("%s %s failure: Data was corrupted: %s",
                         filename.src, filename.operation, e)
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
            if filename.operation != 'list_objects':
                print_op = print_operation(filename, failed,
                                           self.parameters['dryrun'])
                print_dict = {'result': print_op}
                if error_message is not None:
                    print_dict['error'] = error_message
                self.print_queue.put(print_dict)
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
                 print_queue, upload_context, filename):
        self._print_queue = print_queue
        self._upload_context = upload_context
        self._part_number = part_number
        self._chunk_size = chunk_size
        self._filename = filename

    def _read_part(self):
        actual_filename = self._filename.src
        in_file_part_number = self._part_number - 1
        with open(actual_filename, 'rb') as in_file:
            in_file.seek(in_file_part_number * self._chunk_size)
            return in_file.read(self._chunk_size)

    def __call__(self):
        LOGGER.debug("Uploading part %s for filename: %s",
                     self._part_number, self._filename.src)
        try:
            LOGGER.debug("Waiting for upload id.")
            upload_id = self._upload_context.wait_for_upload_id()
            body = self._read_part()
            bucket, key = find_bucket_key(self._filename.dest)
            if sys.version_info[:2] == (2, 6):
                body = StringIO(body)
            else:
                body = bytearray(body)
            params = {'endpoint': self._filename.endpoint,
                      'bucket': bucket, 'key': key,
                      'part_number': str(self._part_number),
                      'upload_id': upload_id,
                      'body': body}
            response_data, http = operate(
                self._filename.service, 'UploadPart', params)
            etag = retrieve_http_etag(http)
            self._upload_context.announce_finished_part(
                etag=etag, part_number=self._part_number)

            print_str = print_operation(self._filename, 0)
            print_result = {'result': print_str}
            total = int(math.ceil(
                self._filename.size/float(self._chunk_size)))
            part_str = {'total': total}
            print_result['part'] = part_str
            self._print_queue.put(print_result)
        except Exception as e:
            LOGGER.debug('Error during part upload: %s' , e,
                         exc_info=True)
            self._upload_context.cancel_upload()
        else:
            LOGGER.debug("Part number %s completed for filename: %s",
                     self._part_number, self._filename.src)


class DownloadPartTask(object):
    """
    This task downloads and writes a part to a file.  This task pulls
    from a ``part_queue`` which represents the queue for a specific
    multipart download.  This pulling from a ``part_queue`` is necessary
    in order to keep track and complete the multipart download initiated by
    the ``FileInfo`` object.
    """
    def __init__(self, session, executer, part_queue, dest_queue,
                 f, region, print_queue, write_lock, part_counter,
                 counter_lock):
        self.session = session
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint(region)
        self.executer = executer
        self.part_queue = part_queue
        self.dest_queue = dest_queue
        self.f = f
        self.print_queue = print_queue
        self.write_lock = write_lock
        self.part_counter = part_counter
        self.counter_lock = counter_lock

    def __call__(self):
        try:
            part_info = self.part_queue.get(True, QUEUE_TIMEOUT_GET)
            with self.counter_lock:
                self.part_counter.count += 1
            filename = part_info[0]
            part_number = part_info[1]
            size_uploads = part_info[2]
            last_part_number = int(filename.size / size_uploads) - 1
            beginning_range = part_number*size_uploads
            str_range = "bytes="
            if part_number == last_part_number:
                str_range += str(beginning_range) + "-"
            else:
                end_range = beginning_range + size_uploads - 1
                str_range += str(beginning_range) + "-" + str(end_range)
            bucket, key = find_bucket_key(filename.src)
            try:
                params = {'endpoint': self.endpoint, 'bucket': bucket,
                          'key': key, 'range': str_range}
                response_data, http = operate(self.service, 'GetObject',
                                              params)
                body = response_data['Body'].read()
                with self.write_lock:
                    self.f.seek(part_number*size_uploads)
                    self.f.write(body)

                print_str = print_operation(filename, 0)
                print_result = {'result': print_str}
                part_str = {'total': int(filename.size / size_uploads)}
                print_result['part'] = part_str
                self.print_queue.put(print_result)
                self.dest_queue.put(part_number)
            except requests.ConnectionError as e:
                connect_error = str(e)
                LOGGER.debug("%s part download failure: %s" %
                            (part_info[0].src, connect_error))
                self.part_queue.put(part_info)
                self.executer.submit(self)
            except Exception as e:
                LOGGER.debug('%s' % str(e))
            self.part_queue.task_done()
            with self.counter_lock:
                self.part_counter.count -= 1
        except Queue.Empty:
            pass


class CreateMultipartUploadTask(BasicTask):
    def __init__(self, session, filename, parameters, print_queue,
                 upload_context):
        super(CreateMultipartUploadTask, self).__init__(
            session, filename, parameters, print_queue)
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
            print_op = print_operation(self.filename, True,
                                        self.parameters['dryrun'])
            print_task = {'result': print_op, 'error': str(e)}
            self.print_queue.put(print_task)
            raise e


class CompleteMultipartUploadTask(BasicTask):
    def __init__(self, session, filename, parameters, print_queue,
                 upload_context):
        super(CompleteMultipartUploadTask, self).__init__(
            session, filename, parameters, print_queue)
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
            print_task = {
                'result': print_operation(self.filename, failed=True,
                                          dryrun=self.parameters['dryrun']),
                'error': str(e)
            }
        else:
            LOGGER.debug("Multipart upload completed for: %s",
                        self.filename.src)
            print_op = print_operation(self.filename, False,
                                       self.parameters['dryrun'])
            print_task = {'result': print_op}
        self.print_queue.put(print_task)


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
        with self._lock:
            self._state = self._COMPLETED

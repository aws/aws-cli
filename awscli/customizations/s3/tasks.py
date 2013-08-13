import copy
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
    operate, retrieve_http_etag, check_etag

LOGGER = logging.getLogger(__name__)


def print_operation(filename, fail, dryrun=False):
    """
    Helper function used to print out what an operation did and whether
    it failed.
    """
    print_str = filename.operation
    if dryrun:
        print_str = '(dryrun) ' + print_str
    if fail:
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
    def __init__(self, session, filename, executer, done, parameters,
                 multi_threshold, chunksize, printQueue, interrupt):
        self.session = session
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint(parameters['region'])

        self.filename = filename
        self.filename.set_session(self.session, parameters['region'])
        self.filename.parameters = parameters

        self.parameters = parameters
        self.multi_threshold = multi_threshold
        self.multi_chunksize = chunksize
        self.executer = executer
        self.printQueue = printQueue
        self.done = done
        self.interrupt = interrupt

    def __call__(self):
        fail = 0
        error = ''
        retry = 0
        filename = self.filename
        try:
            if not self.parameters['dryrun']:
                getattr(filename, filename.operation)()
        except requests.ConnectionError as e:
            retry = 1
            connect_error = str(e)
            LOGGER.debug("%s %s failure: %s" %
                         (filename.src, filename.operation, connect_error))
            self.executer.submit(copy.copy(self))
        except MD5Error as e:
            retry = 1
            LOGGER.debug("%s %s failure: Data was corrupted" %
                         (filename.src, filename.operation))
            self.executer.submit(copy.copy(self))
        except Exception as e:
            fail = 1
            error = str(e)
        try:
            if filename.operation != 'list_objects' and not retry:
                print_op = print_operation(filename, fail,
                                           self.parameters['dryrun'])
                print_dict = {'result': print_op}
                if fail:
                    print_dict['error'] = error
                self.printQueue.put(print_dict)
                pass
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
    def __init__(self, session, executer, part_queue, dest_queue,
                 region, printQueue, interrupt, part_counter):
        self.session = session
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint(region)
        self.executer = executer
        self.part_queue = part_queue
        self.dest_queue = dest_queue
        self.printQueue = printQueue
        self.part_counter = part_counter

    def read_part(self, filename, part_number, part_size):
        num_uploads = int(math.ceil(filename.size/float(part_size)))
        file_loc = filename.src
        in_file_part_number = part_number-1
        with open(file_loc, 'rb') as in_file:
            in_file.seek(in_file_part_number*part_size)
            if part_number == num_uploads:
                return in_file.read()
            else:
                return in_file.read(part_size)

    def __call__(self):
        try:
            part_info = self.part_queue.get(True, QUEUE_TIMEOUT_GET)
            self.part_counter.count += 1
            try:
                filename = part_info[0]
                upload_id = part_info[1]
                part_number = part_info[2]
                part_size = part_info[3]
                body = self.read_part(filename, part_number, part_size)
                bucket, key = find_bucket_key(filename.dest)
                if sys.version_info[:2] == (2, 6):
                    stream_body = StringIO(body)
                else:
                    stream_body = bytearray(body)
                params = {'endpoint': self.endpoint, 'bucket': bucket,
                          'key': key, 'part_number': str(part_number),
                          'upload_id': upload_id,
                          'body': stream_body}
                response_data, http = operate(self.service, 'UploadPart',
                                              params)
                etag = retrieve_http_etag(http)
                check_etag(etag, body)
                parts = {'ETag': etag, 'PartNumber': part_number}
                self.dest_queue.put((part_number, parts))
                print_str = print_operation(filename, 0)
                print_result = {'result': print_str}
                total = int(math.ceil(filename.size/float(part_size)))
                part_str = {'total': total}
                print_result['part'] = part_str
                self.printQueue.put(print_result)
            except requests.ConnectionError as e:
                connect_error = str(e)
                LOGGER.debug("%s part upload failure: %s" %
                             (part_info[0].src, connect_error))
                self.part_queue.put(part_info)
                self.executer.submit(copy.copy(self))
            except MD5Error:
                LOGGER.debug("%s part upload failure: Data"
                             "was corrupted" % part_info[0].src)
                self.part_queue.put(part_info)
                self.executer.submit(copy.copy(self))
            except Exception as e:
                LOGGER.debug('%s' % str(e))
            self.part_queue.task_done()
            self.part_counter.count -= 1
        except Queue.Empty:
                pass


class DownloadPartTask(object):
    """
    This task downloads and writes a part to a file.  This task pulls
    from a ``part_queue`` which represents the queue for a specific
    multipart download.  This pulling from a ``part_queue`` is necessary
    in order to keep track and complete the multipart download initiated by
    the ``FileInfo`` object.
    """
    def __init__(self, session, executer, part_queue, dest_queue,
                 f, region, printQueue, write_lock, part_counter):
        self.session = session
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint(region)
        self.executer = executer
        self.part_queue = part_queue
        self.dest_queue = dest_queue
        self.f = f
        self.printQueue = printQueue
        self.write_lock = write_lock
        self.part_counter = part_counter

    def __call__(self):
        try:
            part_info = self.part_queue.get(True, QUEUE_TIMEOUT_GET)
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
                self.printQueue.put(print_result)
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
            self.part_counter.count -= 1
        except Queue.Empty:
            pass

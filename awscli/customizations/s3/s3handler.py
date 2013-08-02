import hashlib
import logging
import math
import os
try:
    import Queue
except ImportError:
    import queue as Queue
import requests
from six import StringIO
import sys
import threading
import time
try:
    from urllib import quote
except ImportError:
    from urllib.parse import quote

from dateutil.parser import parse
from dateutil.tz import tzlocal

from awscli import EnvironmentVariables
from awscli.customizations.s3.filegenerator import find_bucket_key

LOGGER = logging.getLogger('awscli')


class NoBlockQueue(Queue.Queue):
    """
    This queue ensures that joining does not block interrupt signals.
    It also contains a threading event ``done`` that breaks the
    while loop if signaled
    """
    def __init__(self, done=threading.Event()):
        Queue.Queue.__init__(self)
        self.done = done

    def join(self):
        self.all_tasks_done.acquire()
        try:
            while self.unfinished_tasks:
                if self.done.isSet():
                    break
                self.all_tasks_done.wait(1)
        finally:
            self.all_tasks_done.release()


class MD5Error(Exception):
    """
    Exception for md5's that do not match
    """
    pass


def print_operation(filename, fail, dryrun=0):
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


def make_last_mod_str(last_mod):
    """
    This function creates the last modified time string whenever objects
    or buckets are being listed
    """
    last_mod = parse(last_mod)
    last_mod = last_mod.astimezone(tzlocal())
    last_mod_tup = (str(last_mod.year), str(last_mod.month).zfill(2),
                    str(last_mod.day).zfill(2), str(last_mod.hour).zfill(2),
                    str(last_mod.minute).zfill(2),
                    str(last_mod.second).zfill(2))
    last_mod_str = "%s-%s-%s %s:%s:%s" % last_mod_tup
    return last_mod_str.ljust(19, ' ')


def make_size_str(size):
    """
    This function creates the size string when objects are being listed.
    """
    size_str = str(size)
    return size_str.rjust(10, ' ')


def check_error(response_data):
    """
    A helper function that prints out the error message recieved in the
    response_data and raises an error when there is an error.
    """
    if response_data:
        if 'Errors' in response_data:
            errors = response_data['Errors']
            for error in errors:
                raise Exception("Error: %s\n" % error['Message'])


def retrieve_http_etag(http_response):
    """
    Retrieves etag from http response
    """
    return http_response.headers['ETag'][1:-1]


def check_etag(etag, data):
    """
    This fucntion checks the etag and the md5 checksum to ensure no
    data was corrupted upon transfer
    """
    m = hashlib.md5()
    m.update(data)
    if '-' not in etag:
        if etag != m.hexdigest():
            raise MD5Error


def operate(service, cmd, kwargs):
    """
    A helper function that universally calls any command by taking in the
    service, name of the command, and any additional parameters required in
    the call.
    """
    operation = service.get_operation(cmd)
    http_response, response_data = operation.call(**kwargs)
    check_error(response_data)
    return response_data, http_response


class S3Handler(object):
    """
    This class holds all of the file info objects yielded to it.
    Worker threads take the file info objects and preform the appropriate
    operation.
    """
    def __init__(self, session, params={}, multi_threshold=8*(1024**2),
                 chunksize=7*(1024**2)):
        self.session = session
        self.service = self.session.get_service('s3')
        self.done = threading.Event()
        self.interrupt = threading.Event()
        self.queue = NoBlockQueue(self.interrupt)
        self.lock = threading.Lock()
        self.params = {'dryrun': False, 'quiet': False, 'acl': None}
        self.params['region'] = self.session.get_config()['region']
        for key in self.params.keys():
            if key in params:
                self.params[key] = params[key]
        self.endpoint = self.service.get_endpoint(self.params['region'])
        self.multi_threshold = multi_threshold
        self.chunksize = chunksize
        self.printQueue = NoBlockQueue()
        self.thread_list = []

    def call(self, files):
        LOGGER.debug('Entered S3Handler class')
        self.done.clear()
        self.interrupt.clear()
        current_time = time.time()

        try:
            for i in range(3):
                thread = S3HandlerThread(self.session, self.queue, self.lock,
                                         self.done, self.params,
                                         self.multi_threshold, self.chunksize,
                                         self.printQueue, self.interrupt)
                thread.setDaemon(True)
                self.thread_list.append(thread)
                thread.start()
            print_thread = PrintThread(self.printQueue, self.done,
                                       self.params['quiet'], self.interrupt)
            print_thread.setDaemon(True)
            self.thread_list.append(print_thread)
            print_thread.start()
            tot_files = 0
            tot_parts = 0
            for filename in files:
                num_uploads = 1
                if filename.size > self.multi_threshold:
                    if filename.operation == 'upload':
                        num_uploads = int(math.ceil(filename.size /
                                                    float(self.chunksize)))
                    elif filename.operation == 'download':
                        num_uploads = int(filename.size/self.chunksize)
                self.queue.put(filename)
                tot_files += 1
                tot_parts += num_uploads
            print_thread.totalFiles = tot_files
            print_thread.totalParts = tot_parts
            self.queue.join()
            self.printQueue.join()

        except KeyboardInterrupt:
            self.interrupt.set()
            self.printQueue.put({'result': "Cleaning up. Please wait..."})

        self.done.set()
        for thread in self.thread_list:
            thread.join()
        total_time = time.time() - current_time
        #print total_time


class S3HandlerThread(threading.Thread):
    """
    This is the thread class the preforms the operations on the files
    taken from the s3 handler's queue.
    """
    def __init__(self, session, queue, lock, done, parameters,
                 multi_threshold, chunksize, printQueue, interrupt):
        threading.Thread.__init__(self)
        self.session = session
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint(parameters['region'])
        self.queue = queue
        self.lock = lock
        self.done = done
        self.multi_done = threading.Event()
        self.write_done = threading.Event()
        self.parameters = parameters
        self.multi_threshold = multi_threshold
        self.multi_chunksize = chunksize
        self.printQueue = printQueue
        self.interrupt = interrupt

    def run(self):
        while True:
            try:
                fail = 0
                error = ''
                retry = 0
                filename = self.queue.get(True, 0.5)
                try:
                    if not self.parameters['dryrun']:
                        getattr(self, filename.operation)(filename)
                except requests.ConnectionError as e:
                    retry = 1
                    connect_error = str(e)
                    LOGGER.debug("%s %s failure: %s" %
                                 (filename.src, filename.operation,
                                  connect_error))
                    self.queue.put(filename)
                except MD5Error as e:
                    retry = 1
                    LOGGER.debug("%s %s failure: Data"
                                 "was corrupted" %
                                 (filename.src, filename.operation))
                    self.queue.put(filename)
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
                except Exception:
                    pass
                self.queue.task_done()
            except Queue.Empty:
                pass
            if self.done.isSet():
                break

    def read_file(self, filename):
        """
        This reads the file into a form that can be sent to S3
        """
        with open(filename, 'rb') as in_file:
            return in_file.read()

    def save_file(self, filename, response_data, last_update):
        """
        This writes to the file upon downloading.  It reads the data in the
        response.  Makes a new directory if needed and then writes the
        data to the file.  It also modifies the last modified time to the
        of the s3 file.
        """
        data = response_data['Body'].read()
        etag = response_data['ETag'][1:-1]
        check_etag(etag, data)
        d = os.path.dirname(filename)
        with self.lock:
            if not os.path.exists(d):
                os.makedirs(d)  # to prevent two threads from making same
                                # nonexistant directory
        out_file = open(filename, 'wb')
        out_file.write(data)
        out_file.close()
        last_update_tuple = last_update.timetuple()
        mod_timestamp = time.mktime(last_update_tuple)
        os.utime(filename, (int(mod_timestamp), int(mod_timestamp)))

    def upload(self, filename):
        """
        Redirects the file to the multipart upload function if the file is
        large.  If it is small enough, it puts the file as an object in s3.
        """
        if filename.size < self.multi_threshold:
            body = self.read_file(filename.src)
            bucket, key = find_bucket_key(filename.dest)
            if sys.version_info[:2] == (2, 6):
                stream_body = StringIO(body)
            else:
                stream_body = bytearray(body)
            params = {'endpoint': self.endpoint, 'bucket': bucket,
                      'key': key,
                      'body': stream_body}
            if self.parameters['acl']:
                params['acl'] = self.parameters['acl'][0]
            response_data, http = operate(self.service, 'PutObject', params)
            etag = retrieve_http_etag(http)
            check_etag(etag, body)
        else:
            self.multi_upload(filename)

    def download(self, filename):
        """
        Redirects the file to the multipart download function if the file is
        large.  If it is small enough, it gets the file as an object from s3.
        """
        if filename.size < self.multi_threshold:
            bucket, key = find_bucket_key(filename.src)
            params = {'endpoint': self.endpoint, 'bucket': bucket, 'key': key}
            response_data, http = operate(self.service, 'GetObject', params)
            sys.stdout.flush()
            self.save_file(filename.dest, response_data, filename.last_update)
        else:
            self.multi_download(filename)

    def copy(self, filename):
        """
        Copies a object in s3 to another location in s3.
        """
        copy_source = quote(filename.src)
        bucket, key = find_bucket_key(filename.dest)
        params = {'endpoint': self.endpoint, 'bucket': bucket,
                  'copy_source': copy_source, 'key': key}
        if self.parameters['acl']:
            params['acl'] = self.parameters['acl'][0]
        response_data, http = operate(self.service, 'CopyObject', params)

    def delete(self, filename):
        '''
        Deletes the file from s3 or local.  The src file and type is used
        from the file info object.
        '''
        if (filename.src_type == 's3'):
            bucket, key = find_bucket_key(filename.src)
            params = {'endpoint': self.endpoint, 'bucket': bucket, 'key': key}
            response_data, http = operate(self.service, 'DeleteObject',
                                          params)
        else:
            os.remove(filename.src)

    def move(self, filename):
        """
        Implements a move command for s3
        """
        self.copy(filename)
        self.delete(filename)

    def list_objects(self, filename):
        """
        List all of the buckets if no bucket is specified.  List the objects
        and common prefixes under a specified prefix.
        """
        bucket, key = find_bucket_key(filename.src)
        if bucket == '':
            operation = self.service.get_operation('ListBuckets')
            html_response, response_data = operation.call(self.endpoint)
            header_str = "CreationTime".rjust(19, ' ')
            header_str = header_str + ' ' + "Bucket"
            underline_str = "------------".rjust(19, ' ')
            underline_str = underline_str + ' ' + "------"
            sys.stdout.write("\n%s\n" % header_str)
            sys.stdout.write("%s\n" % underline_str)
            buckets = response_data['Buckets']
            for bucket in buckets:
                last_mod_str = make_last_mod_str(bucket['CreationDate'])
                print_str = last_mod_str + ' ' + bucket['Name']
                sys.stdout.write("%s\n" % print_str)
                sys.stdout.flush()
        else:
            operation = self.service.get_operation('ListObjects')
            iterator = operation.paginate(self.endpoint, bucket=bucket,
                                          prefix=key, delimiter='/')
            sys.stdout.write("\nBucket: %s\n" % bucket)
            sys.stdout.write("Prefix: %s\n\n" % key)
            header_str = "LastWriteTime".rjust(19, ' ')
            header_str = header_str + ' ' + "Length".rjust(10, ' ')
            header_str = header_str + ' ' + "Name"
            underline_str = "-------------".rjust(19, ' ')
            underline_str = underline_str + ' ' + "------".rjust(10, ' ')
            underline_str = underline_str + ' ' + "----"
            sys.stdout.write("%s\n" % header_str)
            sys.stdout.write("%s\n" % underline_str)
            for html_response, response_data in iterator:
                check_error(response_data)
                common_prefixes = response_data['CommonPrefixes']
                contents = response_data['Contents']
                for common_prefix in common_prefixes:
                    prefix_components = common_prefix['Prefix'].split('/')
                    prefix = prefix_components[-2]
                    pre_string = "PRE".rjust(30, " ")
                    print_str = pre_string + ' ' + prefix+'/'
                    sys.stdout.write("%s\n" % print_str)
                    sys.stdout.flush()
                for content in contents:
                    last_mod_str = make_last_mod_str(content['LastModified'])
                    size_str = make_size_str(content['Size'])
                    filename_components = content['Key'].split('/')
                    filename = filename_components[-1]
                    print_str = last_mod_str + ' ' + size_str + ' ' + \
                        filename
                    sys.stdout.write("%s\n" % print_str)
                    sys.stdout.flush()

    def make_bucket(self, filename):
        """
        makes a bucket
        """
        bucket, key = find_bucket_key(filename.src)
        region = self.parameters['region']
        bucket_config = {'LocationConstraint': region}
        params = {'endpoint': self.endpoint, 'bucket': bucket}
        if region != 'us-east-1':
            params['create_bucket_configuration'] = bucket_config
        response_data, http = operate(self.service, 'CreateBucket', params)

    def remove_bucket(self, filename):
        """
        removes a bucket
        """
        bucket, key = find_bucket_key(filename.src)
        params = {'endpoint': self.endpoint, 'bucket': bucket}
        response_data, http = operate(self.service, 'DeleteBucket', params)

    def multi_upload(self, filename):
        """
        Performs multipart uploads.  It initiates the upload.  Instantiate
        threads that get tasks corresponding to read a chunck of the file and
        upload it as a part.  Once all parts are uploaded the multipart
        upload is completed.
        """
        self.multi_done.clear()
        task_queue = NoBlockQueue(self.interrupt)
        complete_upload_queue = Queue.PriorityQueue()
        bucket, key = find_bucket_key(filename.dest)
        params = {'endpoint': self.endpoint, 'bucket': bucket, 'key': key}
        if self.parameters['acl']:
            params['acl'] = self.parameters['acl'][0]
        response_data, http = operate(self.service, 'CreateMultipartUpload',
                                      params)
        upload_id = response_data['UploadId']
        size_uploads = self.multi_chunksize
        num_uploads = int(math.ceil(filename.size/float(size_uploads)))
        thread_list = []
        for i in range(3):
            thread = UploadPartThread(self.session, task_queue,
                                      complete_upload_queue, self.multi_done,
                                      self.parameters['region'],
                                      self.printQueue, self.interrupt)
            thread.setDaemon(True)
            thread_list.append(thread)
            thread.start()
        for i in range(1, (num_uploads + 1)):
            part_info = (filename, upload_id, i, size_uploads)
            task_queue.put(part_info)
        task_queue.join()
        self.multi_done.set()
        for thread in thread_list:
            thread.join()
        parts_list = []
        while not complete_upload_queue.empty():
            part = complete_upload_queue.get()
            parts_list.append(part[1])
        if len(parts_list) == num_uploads:
            parts = {'Parts': parts_list}
            params = {'endpoint': self.endpoint, 'bucket': bucket, 'key': key,
                      'upload_id': upload_id, 'multipart_upload': parts}
            operate(self.service, 'CompleteMultipartUpload', params)
        else:
            abort_params = {'endpoint': self.endpoint, 'bucket': bucket,
                            'key': key, 'upload_id': upload_id}
            operate(self.service, 'AbortMultipartUpload', abort_params)
            raise Exception()

    def multi_download(self, filename):
        """
        This performs the multipart download.  It assigns ranges to get from
        s3 of particular object to a task.  A thread then gets one of these
        tasks gets the object and puts the data on another queue.  Then a
        single thread pulls the data off of the queue and writes to the file.
        The last modification time is changed to the last modification time
        of the s3 object
        """
        self.multi_done.clear()
        self.write_done.clear()
        task_queue = NoBlockQueue(self.interrupt)
        write_queue = NoBlockQueue(self.interrupt)
        d = os.path.dirname(filename.dest)
        with self.lock:
            if not os.path.exists(d):
                os.makedirs(d)  # to prevent two threads from making same
                                # nonexistant directory
        size_uploads = self.multi_chunksize
        num_uploads = int(filename.size/size_uploads)
        with open(filename.dest, 'wb') as f:
            thread_list = []
            for i in range(2):
                thread = DownloadPartThread(self.session, task_queue,
                                            write_queue, self.multi_done,
                                            self.parameters['region'],
                                            self.printQueue, self.interrupt)
                thread.setDaemon(True)
                thread_list.append(thread)
                thread.start()
            write_thread = WriteFile(self.session, f, write_queue,
                                     self.write_done, self.interrupt)
            write_thread.setDaemon(True)
            write_thread.start()
            for i in range(num_uploads):
                task = (filename, i, size_uploads)
                task_queue.put(task)
            task_queue.join()
            self.multi_done.set()
            for thread in thread_list:
                thread.join()
            write_queue.join()
            self.write_done.set()
            download_failed = write_thread.failed
            write_thread.join()
        last_update_tuple = filename.last_update.timetuple()
        mod_timestamp = time.mktime(last_update_tuple)
        os.utime(filename.dest, (int(mod_timestamp), int(mod_timestamp)))
        if download_failed:
            raise Exception()


class DownloadPartThread(threading.Thread):
    """
    This thread obtains the range of bytes from an object in s3
    and stores the data onanother queue that is used to write to the local
    file.
    """
    def __init__(self, session, queue, write_queue,
                 multi_done, region, printQueue, interrupt):
        threading.Thread.__init__(self)
        self.session = session
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint(region)
        self.queue = queue
        self.write_queue = write_queue
        self.multi_done = multi_done
        self.printQueue = printQueue
        self.interrupt = interrupt

    def run(self):
        while True:
            try:
                part_info = self.queue.get(True, 0.5)
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
                    write_task = (part_number, size_uploads, body)
                    self.write_queue.put(write_task)
                    print_str = print_operation(filename, 0)
                    print_result = {'result': print_str}
                    part_str = {'total': int(filename.size / size_uploads)}
                    print_result['part'] = part_str
                    self.printQueue.put(print_result)
                except requests.ConnectionError as e:
                    connect_error = str(e)
                    LOGGER.debug("%s part download failure: %s" %
                                 (part_info[0].src, connect_error))
                    self.queue.put(part_info)
                except Exception:
                    self.write_queue.put(['fail', '', ''])
                self.queue.task_done()
            except Queue.Empty:
                pass
            if self.multi_done.isSet() or self.interrupt.isSet():
                break


class WriteFile(threading.Thread):
    """
    This thread takes data off the write queue and writes it to the
    local file.
    """
    def __init__(self, session, f, write_queue, write_done, interrupt):
        threading.Thread.__init__(self)
        self.session = session
        self.f = f
        self.queue = write_queue
        self.write_done = write_done
        self.m = hashlib.md5()
        self.failed = False
        self.interrupt = interrupt

    def run(self):
        while True:
            try:
                write_task = self.queue.get(True, 0.5)
                part_number = write_task[0]
                if part_number != 'fail':
                    size_uploads = write_task[1]
                    body = write_task[2]
                    self.f.seek(part_number*size_uploads)
                    self.f.write(body)
                else:
                    self.failed = True
                self.queue.task_done()
            except Queue.Empty:
                pass
            if self.write_done.isSet() or self.interrupt.isSet():
                break


class UploadPartThread(threading.Thread):
    """
    This thread reads an assigned part in the file and uploads it as
    a part to s3.
    """
    def __init__(self, session, queue, dest_queue,
                 multi_done, region, printQueue, interrupt):
        threading.Thread.__init__(self)
        self.session = session
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint(region)
        self.queue = queue
        self.dest_queue = dest_queue
        self.multi_done = multi_done
        self.printQueue = printQueue
        self.interrupt = interrupt

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

    def run(self):
        while True:
            try:
                part_info = self.queue.get(True, 0.5)
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
                              'key': key, 'part_number': part_number,
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
                    self.queue.put(part_info)
                except MD5Error:
                    LOGGER.debug("%s part upload failure: Data"
                                 "was corrupted" % part_info[0].src)
                    self.queue.put(part_info)
                except Exception:
                    pass
                self.queue.task_done()
            except Queue.Empty:
                pass
            if self.multi_done.isSet() or self.interrupt.isSet():
                break


class PrintThread(threading.Thread):
    """
    This thread controls the printing of results.  When a task is
    completely finished it is permanently write the result to standard
    out. Otherwise, it is a part of a multipart upload/download and
    only shows the most current part upload/download.
    """
    def __init__(self, printQueue, done, quiet, interrupt):
        threading.Thread.__init__(self)
        self.progress_dict = {}
        self.printQueue = printQueue
        self.done = done
        self.quiet = quiet
        self.progressLength = 0
        self.interrupt = interrupt
        self.numParts = 0
        self.totalParts = 0
        self.totalFiles = '...'
        self.file_count = 0

    def run(self):
        while True:
            try:
                print_task = self.printQueue.get(True, 0.5)
                print_str = print_task['result']
                final_str = ''
                if print_task.get('part', ''):
                    # Normalize keys so failures and sucess
                    # look the same.
                    op_list = print_str.split(':')
                    print_str = ':'.join(op_list[1:])
                    print_part = print_task['part']
                    total_part = print_part['total']
                    self.numParts += 1
                    if print_str in self.progress_dict:
                        self.progress_dict[print_str]['parts'] += 1
                    else:
                        self.progress_dict[print_str] = {}
                        self.progress_dict[print_str]['parts'] = 1
                        self.progress_dict[print_str]['total'] = total_part
                else:
                    print_components = print_str.split(':')
                    error = print_components[0].endswith('failed')
                    final_str += print_str.ljust(self.progressLength, ' ')
                    final_str += '\n'
                    if print_task.get('error', ''):
                        final_str += print_task['error'] + '\n'
                    key = ':'.join(print_components[1:])
                    if key in self.progress_dict:
                        self.progress_dict.pop(print_str, None)
                    else:
                        self.numParts += 1
                    self.file_count += 1

                current_files = self.progress_dict.keys()
                total_files = len(current_files)
                total_parts = 0
                completed_parts = 0
                is_done = self.totalFiles == self.file_count
                if not self.interrupt.isSet() and not is_done:
                    prog_str = "Completed %s " % self.numParts
                    num_files = self.totalFiles
                    if self.totalFiles != '...':
                        prog_str += "of %s " % self.totalParts
                        num_files = self.totalFiles - self.file_count
                    prog_str += "part(s) with %s file(s) remaining" % \
                        num_files
                    length_prog = len(prog_str)
                    prog_str += '\r'
                    prog_str = prog_str.ljust(self.progressLength, ' ')
                    self.progressLength = length_prog
                    final_str += prog_str
                if not self.quiet:
                    sys.stdout.write(final_str)
                    sys.stdout.flush()
                self.printQueue.task_done()
            except Queue.Empty:
                pass
            if self.done.isSet():
                break

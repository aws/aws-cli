import math
import os
from six import StringIO
from six.moves import queue as Queue
import sys
import time
import threading

from dateutil.parser import parse
from dateutil.tz import tzlocal

from botocore.compat import quote
from awscli.customizations.s3.tasks import UploadPartTask, DownloadPartTask
from awscli.customizations.s3.utils import find_bucket_key, MultiCounter, \
    retrieve_http_etag, check_etag, check_error, operate, NoBlockQueue


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


def read_file(filename):
    """
    This reads the file into a form that can be sent to S3
    """
    with open(filename, 'rb') as in_file:
        return in_file.read()


def save_file(filename, response_data, last_update):
    """
    This writes to the file upon downloading.  It reads the data in the
    response.  Makes a new directory if needed and then writes the
    data to the file.  It also modifies the last modified time to that
    of the S3 object.
    """
    data = response_data['Body'].read()
    etag = response_data['ETag'][1:-1]
    check_etag(etag, data)
    d = os.path.dirname(filename)
    try:
        if not os.path.exists(d):
            os.makedirs(d)
    except Exception:
        pass
    with open(filename, 'wb') as out_file:
        out_file.write(data)
    last_update_tuple = last_update.timetuple()
    mod_timestamp = time.mktime(last_update_tuple)
    os.utime(filename, (int(mod_timestamp), int(mod_timestamp)))


class TaskInfo(object):
    """
    This class contains important details related to performing a task.  This
    object is usually only used for creating buckets, removing buckets, and
    listing objects/buckets.  This object contains the attributes and
    functions needed to perform the task.  Note that just instantiating one
    of these objects will not be enough to run a listing or bucket command.
    unless ``session`` and ``region`` are specified upon instantiation.
    To make it fully operational, ``set_session`` needs to be used.
    This class is the parent class of the more extensive ``FileInfo`` object.

    :param src: the source path
    :type src: string
    :param src_type: if the source file is s3 or local.
    :type src_type: string
    :param operation: the operation being performed.
    :type operation: string
    :param session: ``botocore.session`` object
    :param region: The region for the endpoint

    Note that a local file will always have its absolute path, and a s3 file
    will have its path in the form of bucket/key
    """
    def __init__(self, src, src_type=None, operation=None, session=None,
                 region=None):
        self.src = src
        self.src_type = src_type
        self.operation = operation

        self.session = session
        self.region = region
        self.service = None
        self.endpoint = None
        if self.session and self.region:
            self.set_session(self.session, self.region)

    def set_session(self, session, region):
        """
        Given a session and region set the service and endpoint.  This enables
        operations to be performed as ``self.session`` is required to perform
        an operation.
        """
        self.session = session
        self.region = region
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint(self.region)

    def list_objects(self):
        """
        List all of the buckets if no bucket is specified.  List the objects
        and common prefixes under a specified prefix.
        """
        bucket, key = find_bucket_key(self.src)
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

    def make_bucket(self):
        """
        This opereation makes a bucket.
        """
        bucket, key = find_bucket_key(self.src)
        bucket_config = {'LocationConstraint': self.region}
        params = {'endpoint': self.endpoint, 'bucket': bucket}
        if self.region != 'us-east-1':
            params['create_bucket_configuration'] = bucket_config
        response_data, http = operate(self.service, 'CreateBucket', params)

    def remove_bucket(self):
        """
        This operation removes a bucket.
        """
        bucket, key = find_bucket_key(self.src)
        params = {'endpoint': self.endpoint, 'bucket': bucket}
        response_data, http = operate(self.service, 'DeleteBucket', params)


class FileInfo(TaskInfo):
    """
    This is a child object of the ``TaskInfo`` object.  It can perform more
    operations such as ``upload``, ``download``, ``copy``, ``delete``,
    ``move``, `multi_upload``, and ``multi_download``.  Similiarly to
    ``TaskInfo`` objects attributes like ``session`` need to be set in order
    to perform operations. Multipart operations need to run ``set_multi`` in
    order to be able to run.
    :param dest: the destination path
    :type dest: string
    :param compare_key: the name of the file relative to the specified
        directory/prefix.  This variable is used when performing synching
        or if the destination file is adopting the source file's name.
    :type compare_key: string
    :param size: The size of the file in bytes.
    :type size: integer
    :param last_update: the local time of last modification.
    :type last_update: datetime object
    :param dest_type: if the destination is s3 or local.
    :param dest_type: string
    :param parameters: a dictionary of important values this is assigned in
        the ``BasicTask`` object.
    """
    def __init__(self, src, dest=None, compare_key=None, size=None,
                 last_update=None, src_type=None, dest_type=None,
                 operation=None, session=None, region=None, parameters=None):
        super(FileInfo, self).__init__(src, src_type=src_type,
                                       operation=operation, session=session,
                                       region=region)
        self.dest = dest
        self.dest_type = dest_type
        self.compare_key = compare_key
        self.size = size
        self.last_update = last_update
        # Usually inject ``parameters`` from ``BasicTask`` class.
        if parameters:
            self.parameters = parameters
        else:
            self.parameters = {'acl': None}

        # Required for multipart uploads and downloads.  Use ``set_multi``
        # function to set these.
        self.executer = None
        self.printQueue = None
        self.is_multi = False
        self.interrupt = None
        self.chunksize = None

    def set_multi(self, executer, printQueue, interrupt, chunksize):
        """
        This sets all of the necessary attributes to perform a multipart
        operation.
        """
        self.executer = executer
        self.printQueue = printQueue
        self.is_multi = True
        self.interrupt = interrupt
        self.chunksize = chunksize

    def upload(self):
        """
        Redirects the file to the multipart upload function if the file is
        large.  If it is small enough, it puts the file as an object in s3.
        """
        if not self.is_multi:
            body = read_file(self.src)
            bucket, key = find_bucket_key(self.dest)
            if sys.version_info[:2] == (2, 6):
                stream_body = StringIO(body)
            else:
                stream_body = bytearray(body)
            params = {'endpoint': self.endpoint, 'bucket': bucket, 'key': key}
            if body:
                params['body'] = stream_body
            if self.parameters['acl']:
                params['acl'] = self.parameters['acl'][0]
            response_data, http = operate(self.service, 'PutObject', params)
            etag = retrieve_http_etag(http)
            check_etag(etag, body)
        else:
            self.multi_upload()

    def download(self):
        """
        Redirects the file to the multipart download function if the file is
        large.  If it is small enough, it gets the file as an object from s3.
        """
        if not self.is_multi:
            bucket, key = find_bucket_key(self.src)
            params = {'endpoint': self.endpoint, 'bucket': bucket, 'key': key}
            response_data, http = operate(self.service, 'GetObject', params)
            save_file(self.dest, response_data, self.last_update)
        else:
            self.multi_download()

    def copy(self):
        """
        Copies a object in s3 to another location in s3.
        """
        copy_source = quote(self.src)
        bucket, key = find_bucket_key(self.dest)
        params = {'endpoint': self.endpoint, 'bucket': bucket,
                  'copy_source': copy_source, 'key': key}
        if self.parameters['acl']:
            params['acl'] = self.parameters['acl'][0]
        response_data, http = operate(self.service, 'CopyObject', params)

    def delete(self):
        """
        Deletes the file from s3 or local.  The src file and type is used
        from the file info object.
        """
        if (self.src_type == 's3'):
            bucket, key = find_bucket_key(self.src)
            params = {'endpoint': self.endpoint, 'bucket': bucket, 'key': key}
            response_data, http = operate(self.service, 'DeleteObject',
                                          params)
        else:
            os.remove(self.src)

    def move(self):
        """
        Implements a move command for s3.
        """
        src = self.src_type
        dest = self.dest_type
        if src == 'local' and dest == 's3':
            self.upload()
        elif src == 's3' and dest == 's3':
            self.copy()
        elif src == 's3' and dest == 'local':
            self.download()
        else:
            raise Exception("Invalid path arguments for mv")
        self.delete()

    def multi_upload(self):
        """
        Performs multipart uploads.  It initiates the multipart upload.
        It creates a queue ``part_queue`` which is directly responsible
        with controlling the progress of the multipart upload.  It then
        creates ``UploadPartTasks`` for threads to run via the
        ``executer``.  This fucntion waits for all of the parts in the
        multipart upload to finish, and then it completes the multipart
        upload.  This method waits on its parts to finish.  So, threads
        are required to process the parts for this function to complete.
        """
        part_queue = NoBlockQueue(self.interrupt)
        complete_upload_queue = Queue.PriorityQueue()
        part_counter = MultiCounter()
        bucket, key = find_bucket_key(self.dest)
        params = {'endpoint': self.endpoint, 'bucket': bucket, 'key': key}
        if self.parameters['acl']:
            params['acl'] = self.parameters['acl'][0]
        response_data, http = operate(self.service, 'CreateMultipartUpload',
                                      params)
        upload_id = response_data['UploadId']
        size_uploads = self.chunksize
        num_uploads = int(math.ceil(self.size/float(size_uploads)))
        for i in range(1, (num_uploads + 1)):
            part_info = (self, upload_id, i, size_uploads)
            part_queue.put(part_info)
            task = UploadPartTask(session=self.session, executer=self.executer,
                                  part_queue=part_queue,
                                  dest_queue=complete_upload_queue,
                                  region=self.region,
                                  printQueue=self.printQueue,
                                  interrupt=self.interrupt,
                                  part_counter=part_counter)
            self.executer.submit(task)
        part_queue.join()
        # The following ensures that if the multipart upload is in progress,
        # all part uploads finish before aborting or completing.  This
        # really only applies when an interrupt signal is sent because the
        # ``part_queue.join()`` ensures this if the process is not
        # interrupted.
        while part_counter.count:
            time.sleep(0.1)
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

    def multi_download(self):
        """
        This performs the multipart download.  It assigns ranges to get from
        s3 of particular object to a task.It creates a queue ``part_queue``
        which is directly responsible with controlling the progress of the
        multipart download.  It then creates ``DownloadPartTasks`` for
        threads to run via the ``executer``. This fucntion waits
        for all of the parts in the multipart download to finish, and then
        the last modification time is changed to the last modified time
        of the s3 object.  This method waits on its parts to finish.
        So, threads are required to process the parts for this function
        to complete.
        """
        part_queue = NoBlockQueue(self.interrupt)
        dest_queue = NoBlockQueue(self.interrupt)
        part_counter = MultiCounter()
        write_lock = threading.Lock()
        d = os.path.dirname(self.dest)
        try:
            if not os.path.exists(d):
                os.makedirs(d)
        except Exception:
            pass
        size_uploads = self.chunksize
        num_uploads = int(self.size/size_uploads)
        with open(self.dest, 'wb') as f:
            for i in range(num_uploads):
                part = (self, i, size_uploads)
                part_queue.put(part)
                task = DownloadPartTask(session=self.session,
                                        executer=self.executer,
                                        part_queue=part_queue,
                                        dest_queue=dest_queue,
                                        f=f, region=self.region,
                                        printQueue=self.printQueue,
                                        write_lock=write_lock,
                                        part_counter=part_counter)
                self.executer.submit(task)
            part_queue.join()
            # The following ensures that if the multipart download is
            # in progress, all part uploads finish before releasing the
            # the file handle.  This really only applies when an interrupt
            # signal is sent because the ``part_queue.join()`` ensures this
            # if the process is not interrupted.
            while part_counter.count:
                time.sleep(0.1)
        part_list = []
        while not dest_queue.empty():
            part = dest_queue.get()
            part_list.append(part)
        if len(part_list) != num_uploads:
            raise Exception()
        last_update_tuple = self.last_update.timetuple()
        mod_timestamp = time.mktime(last_update_tuple)
        os.utime(self.dest, (int(mod_timestamp), int(mod_timestamp)))

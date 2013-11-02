import os
import sys
import time
from functools import partial
import hashlib

from dateutil.parser import parse
from dateutil.tz import tzlocal

from botocore.compat import quote
from awscli.customizations.s3.utils import find_bucket_key, \
        check_etag, check_error, operate, uni_print, \
        guess_content_type, MD5Error


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
    body = response_data['Body']
    etag = response_data['ETag'][1:-1]
    d = os.path.dirname(filename)
    try:
        if not os.path.exists(d):
            os.makedirs(d)
    except Exception:
        pass
    md5 = hashlib.md5()
    file_chunks = iter(partial(body.read, 1024 * 1024), b'')
    with open(filename, 'wb') as out_file:
        if not _is_multipart_etag(etag):
            for chunk in file_chunks:
                md5.update(chunk)
                out_file.write(chunk)
        else:
            for chunk in file_chunks:
                out_file.write(chunk)
    if not _is_multipart_etag(etag):
        if etag != md5.hexdigest():
            os.remove(filename)
            raise MD5Error(filename)
    last_update_tuple = last_update.timetuple()
    mod_timestamp = time.mktime(last_update_tuple)
    os.utime(filename, (int(mod_timestamp), int(mod_timestamp)))


def _is_multipart_etag(etag):
    return '-' in etag


class TaskInfo(object):
    """
    This class contains important details related to performing a task.  This
    object is usually only used for creating buckets, removing buckets, and
    listing objects/buckets.  This object contains the attributes and
    functions needed to perform the task.  Note that just instantiating one
    of these objects will not be enough to run a listing or bucket command.
    unless ``session`` and ``region`` are specified upon instantiation.

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
    def __init__(self, src, src_type, operation_name, service, endpoint):
        self.src = src
        self.src_type = src_type
        self.operation_name = operation_name
        self.service = service
        self.endpoint = endpoint

    def make_bucket(self):
        """
        This opereation makes a bucket.
        """
        bucket, key = find_bucket_key(self.src)
        bucket_config = {'LocationConstraint': self.endpoint.region_name}
        params = {'endpoint': self.endpoint, 'bucket': bucket}
        if self.endpoint.region_name != 'us-east-1':
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
    ``move``.  Similiarly to
    ``TaskInfo`` objects attributes like ``session`` need to be set in order
    to perform operations.

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
                 operation_name=None, service=None, endpoint=None,
                 parameters=None):
        super(FileInfo, self).__init__(src, src_type=src_type,
                                       operation_name=operation_name,
                                       service=service,
                                       endpoint=endpoint)
        self.dest = dest
        self.dest_type = dest_type
        self.compare_key = compare_key
        self.size = size
        self.last_update = last_update
        # Usually inject ``parameters`` from ``BasicTask`` class.
        if parameters is not None:
            self.parameters = parameters
        else:
            self.parameters = {'acl': None,
                               'sse': None}

    def _permission_to_param(self, permission):
        if permission == 'read':
            return 'grant_read'
        if permission == 'full':
            return 'grant_full_control'
        if permission == 'readacl':
            return 'grant_read_acp'
        if permission == 'writeacl':
            return 'grant_write_acp'
        raise ValueError('permission must be one of: '
                         'read|readacl|writeacl|full')

    def _handle_object_params(self, params):
        if self.parameters['acl']:
            params['acl'] = self.parameters['acl'][0]
        if self.parameters['grants']:
            for grant in self.parameters['grants']:
                try:
                    permission, grantee = grant.split('=', 1)
                except ValueError:
                    raise ValueError('grants should be of the form '
                                     'permission=principal')
                params[self._permission_to_param(permission)] = grantee
        if self.parameters['sse']:
            params['server_side_encryption'] = 'AES256'
        if self.parameters['storage_class']:
            params['storage_class'] = self.parameters['storage_class'][0]
        if self.parameters['website_redirect']:
            params['website_redirect_location'] = \
                    self.parameters['website_redirect'][0]
        if self.parameters['guess_mime_type']:
            self._inject_content_type(params, self.src)
        if self.parameters['content_type']:
            params['content_type'] = self.parameters['content_type'][0]
        if self.parameters['cache_control']:
            params['cache_control'] = self.parameters['cache_control'][0]
        if self.parameters['content_disposition']:
            params['content_disposition'] = \
                    self.parameters['content_disposition'][0]
        if self.parameters['content_encoding']:
            params['content_encoding'] = self.parameters['content_encoding'][0]
        if self.parameters['content_language']:
            params['content_language'] = self.parameters['content_language'][0]
        if self.parameters['expires']:
            params['expires'] = self.parameters['expires'][0]

    def upload(self):
        """
        Redirects the file to the multipart upload function if the file is
        large.  If it is small enough, it puts the file as an object in s3.
        """
        with open(self.src, 'rb') as body:
            bucket, key = find_bucket_key(self.dest)
            params = {
                'endpoint': self.endpoint,
                'bucket': bucket,
                'key': key,
                'body': body,
            }
            self._handle_object_params(params)
            response_data, http = operate(self.service, 'PutObject', params)
            etag = response_data['ETag'][1:-1]
            body.seek(0)
            check_etag(etag, body)

    def _inject_content_type(self, params, filename):
        # Add a content type param if we can guess the type.
        guessed_type = guess_content_type(filename)
        if guessed_type is not None:
            params['content_type'] = guessed_type

    def download(self):
        """
        Redirects the file to the multipart download function if the file is
        large.  If it is small enough, it gets the file as an object from s3.
        """
        bucket, key = find_bucket_key(self.src)
        params = {'endpoint': self.endpoint, 'bucket': bucket, 'key': key}
        response_data, http = operate(self.service, 'GetObject', params)
        save_file(self.dest, response_data, self.last_update)

    def copy(self):
        """
        Copies a object in s3 to another location in s3.
        """
        copy_source = quote(self.src.encode('utf-8'), safe='/~')
        bucket, key = find_bucket_key(self.dest)
        params = {'endpoint': self.endpoint, 'bucket': bucket,
                  'copy_source': copy_source, 'key': key}
        self._handle_object_params(params)
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

    def create_multipart_upload(self):
        bucket, key = find_bucket_key(self.dest)
        params = {'endpoint': self.endpoint, 'bucket': bucket, 'key': key}
        self._handle_object_params(params)
        response_data, http = operate(self.service, 'CreateMultipartUpload',
                                      params)
        upload_id = response_data['UploadId']
        return upload_id

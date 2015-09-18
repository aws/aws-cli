import os
import sys
import time
from functools import partial
import errno
import hashlib

from dateutil.parser import parse
from dateutil.tz import tzlocal

from botocore.compat import quote
from awscli.customizations.s3.utils import find_bucket_key, \
    uni_print, guess_content_type, MD5Error, bytes_print


class CreateDirectoryError(Exception):
    pass


def read_file(filename):
    """
    This reads the file into a form that can be sent to S3
    """
    with open(filename, 'rb') as in_file:
        return in_file.read()


def save_file(filename, response_data, last_update, is_stream=False):
    """
    This writes to the file upon downloading.  It reads the data in the
    response.  Makes a new directory if needed and then writes the
    data to the file.  It also modifies the last modified time to that
    of the S3 object.
    """
    body = response_data['Body']
    etag = response_data['ETag'][1:-1]
    sse = response_data.get('ServerSideEncryption', None)
    if not is_stream:
        d = os.path.dirname(filename)
        try:
            if not os.path.exists(d):
                os.makedirs(d)
        except OSError as e:
            if not e.errno == errno.EEXIST:
                raise CreateDirectoryError(
                    "Could not create directory %s: %s" % (d, e))
    md5 = hashlib.md5()
    file_chunks = iter(partial(body.read, 1024 * 1024), b'')
    if is_stream:
        # Need to save the data to be able to check the etag for a stream
        # because once the data is written to the stream there is no
        # undoing it.
        payload = write_to_file(None, etag, md5, file_chunks, True)
    else:
        with open(filename, 'wb') as out_file:
            write_to_file(out_file, etag, md5, file_chunks)

    if not _is_multipart_etag(etag) and sse != 'aws:kms':
        if etag != md5.hexdigest():
            if not is_stream:
                os.remove(filename)
            raise MD5Error(filename)

    if not is_stream:
        last_update_tuple = last_update.timetuple()
        mod_timestamp = time.mktime(last_update_tuple)
        os.utime(filename, (int(mod_timestamp), int(mod_timestamp)))
    else:
        # Now write the output to stdout since the md5 is correct.
        bytes_print(payload)
        sys.stdout.flush()


def write_to_file(out_file, etag, md5, file_chunks, is_stream=False):
    """
    Updates the etag for each file chunk.  It will write to the file if it a
    file but if it is a stream it will return a byte string to be later
    written to a stream.
    """
    body = b''
    for chunk in file_chunks:
        if not _is_multipart_etag(etag):
            md5.update(chunk)
        if is_stream:
            body += chunk
        else:
            out_file.write(chunk)
    return body


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
    def __init__(self, src, src_type, operation_name, client):
        self.src = src
        self.src_type = src_type
        self.operation_name = operation_name
        self.client = client

    def make_bucket(self):
        """
        This opereation makes a bucket.
        """
        bucket, key = find_bucket_key(self.src)
        bucket_config = {'LocationConstraint': self.client.meta.region_name}
        params = {'Bucket': bucket}
        if self.client.meta.region_name != 'us-east-1':
            params['CreateBucketConfiguration'] = bucket_config
        self.client.create_bucket(**params)

    def remove_bucket(self):
        """
        This operation removes a bucket.
        """
        bucket, key = find_bucket_key(self.src)
        self.client.delete_bucket(Bucket=bucket)


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
                 operation_name=None, client=None, parameters=None,
                 source_client=None, is_stream=False):
        super(FileInfo, self).__init__(src, src_type=src_type,
                                       operation_name=operation_name,
                                       client=client)
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
        self.source_client = source_client
        self.is_stream = is_stream

    def set_size_from_s3(self):
        """
        This runs a ``HeadObject`` on the s3 object and sets the size.
        """
        bucket, key = find_bucket_key(self.src)
        params = {'Bucket': bucket,
                  'Key': key}
        response_data = self.client.head_object(**params)
        self.size = int(response_data['ContentLength'])

    def _permission_to_param(self, permission):
        if permission == 'read':
            return 'GrantRead'
        if permission == 'full':
            return 'GrantFullControl'
        if permission == 'readacl':
            return 'GrantReadACP'
        if permission == 'writeacl':
            return 'GrantWriteACP'
        raise ValueError('permission must be one of: '
                         'read|readacl|writeacl|full')

    def _handle_object_params(self, params):
        if self.parameters['acl']:
            params['ACL'] = self.parameters['acl'][0]
        if self.parameters['grants']:
            for grant in self.parameters['grants']:
                try:
                    permission, grantee = grant.split('=', 1)
                except ValueError:
                    raise ValueError('grants should be of the form '
                                     'permission=principal')
                params[self._permission_to_param(permission)] = grantee
        if self.parameters['sse']:
            params['ServerSideEncryption'] = 'AES256'
        if self.parameters['storage_class']:
            params['StorageClass'] = self.parameters['storage_class'][0]
        if self.parameters['website_redirect']:
            params['WebsiteRedirectLocation'] = \
                    self.parameters['website_redirect'][0]
        if self.parameters['guess_mime_type']:
            self._inject_content_type(params, self.src)
        if self.parameters['content_type']:
            params['ContentType'] = self.parameters['content_type'][0]
        if self.parameters['cache_control']:
            params['CacheControl'] = self.parameters['cache_control'][0]
        if self.parameters['content_disposition']:
            params['ContentDisposition'] = \
                    self.parameters['content_disposition'][0]
        if self.parameters['content_encoding']:
            params['ContentEncoding'] = self.parameters['content_encoding'][0]
        if self.parameters['content_language']:
            params['ContentLanguage'] = self.parameters['content_language'][0]
        if self.parameters['expires']:
            params['Expires'] = self.parameters['expires'][0]

    def _handle_metadata_directive(self, params):
        if self.parameters['metadata_directive']:
            params['MetadataDirective'] = \
                self.parameters['metadata_directive'][0]

    def upload(self, payload=None):
        """
        Redirects the file to the multipart upload function if the file is
        large.  If it is small enough, it puts the file as an object in s3.
        """
        if payload:
            self._handle_upload(payload)
        else:
            with open(self.src, 'rb') as body:
                self._handle_upload(body)

    def _handle_upload(self, body):
        bucket, key = find_bucket_key(self.dest)
        params = {
            'Bucket': bucket,
            'Key': key,
            'Body': body,
        }
        self._handle_object_params(params)
        response_data = self.client.put_object(**params)

    def _inject_content_type(self, params, filename):
        # Add a content type param if we can guess the type.
        guessed_type = guess_content_type(filename)
        if guessed_type is not None:
            params['ContentType'] = guessed_type

    def download(self):
        """
        Redirects the file to the multipart download function if the file is
        large.  If it is small enough, it gets the file as an object from s3.
        """
        bucket, key = find_bucket_key(self.src)
        params = {'Bucket': bucket, 'Key': key}
        response_data = self.client.get_object(**params)
        save_file(self.dest, response_data, self.last_update,
                  self.is_stream)

    def copy(self):
        """
        Copies a object in s3 to another location in s3.
        """
        copy_source = self.src
        bucket, key = find_bucket_key(self.dest)
        params = {'Bucket': bucket,
                  'CopySource': copy_source, 'Key': key}
        self._handle_object_params(params)
        self._handle_metadata_directive(params)
        self.client.copy_object(**params)

    def delete(self):
        """
        Deletes the file from s3 or local.  The src file and type is used
        from the file info object.
        """
        if self.src_type == 's3':
            bucket, key = find_bucket_key(self.src)
            params = {'Bucket': bucket, 'Key': key}
            self.source_client.delete_object(**params)
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
        params = {'Bucket': bucket, 'Key': key}
        self._handle_object_params(params)
        response_data = self.client.create_multipart_upload(**params)
        upload_id = response_data['UploadId']
        return upload_id

import os
import logging
import sys
import time
from functools import partial
import errno
import hashlib

from botocore.compat import MD5_AVAILABLE
from awscli.customizations.s3.utils import (
    find_bucket_key, guess_content_type, CreateDirectoryError, MD5Error,
    bytes_print, set_file_utime, RequestParamsMapper)
from awscli.compat import bytes_print


LOGGER = logging.getLogger(__name__)


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
    if not is_stream:
        d = os.path.dirname(filename)
        try:
            if not os.path.exists(d):
                os.makedirs(d)
        except OSError as e:
            if not e.errno == errno.EEXIST:
                raise CreateDirectoryError(
                    "Could not create directory %s: %s" % (d, e))

    if MD5_AVAILABLE and _can_validate_md5_with_etag(etag, response_data):
        md5 = hashlib.md5()
    else:
        md5 = None

    file_chunks = iter(partial(body.read, 1024 * 1024), b'')
    if is_stream:
        # Need to save the data to be able to check the etag for a stream
        # because once the data is written to the stream there is no
        # undoing it.
        payload = write_to_file(None, etag, file_chunks, md5, True)
    else:
        with open(filename, 'wb') as out_file:
            write_to_file(out_file, etag, file_chunks, md5)

    if md5 is not None and etag != md5.hexdigest():
        if not is_stream:
            os.remove(filename)
        raise MD5Error(filename)

    if not is_stream:
        last_update_tuple = last_update.timetuple()
        mod_timestamp = time.mktime(last_update_tuple)
        set_file_utime(filename, int(mod_timestamp))
    else:
        # Now write the output to stdout since the md5 is correct.
        bytes_print(payload)
        sys.stdout.flush()


def _can_validate_md5_with_etag(etag, response_data):
    sse = response_data.get('ServerSideEncryption', None)
    sse_customer_algorithm = response_data.get('SSECustomerAlgorithm', None)
    if not _is_multipart_etag(etag) and sse != 'aws:kms' and \
            sse_customer_algorithm is None:
        return True
    return False


def write_to_file(out_file, etag, file_chunks, md5=None, is_stream=False):
    """
    Updates the etag for each file chunk.  It will write to the file if it a
    file but if it is a stream it will return a byte string to be later
    written to a stream.
    """
    body = b''
    for chunk in file_chunks:
        if md5 is not None and not _is_multipart_etag(etag):
            md5.update(chunk)
        if is_stream:
            body += chunk
        else:
            out_file.write(chunk)
    return body


def _is_multipart_etag(etag):
    return '-' in etag


class FileInfo(object):
    """This class contains important details related to performing a task.

    It can perform operations such as ``upload``, ``download``, ``copy``,
    ``delete``, ``move``.  Similarly to ``TaskInfo`` objects attributes
    like ``session`` need to be set in order to perform operations.

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
    :param associated_response_data: The response data used by
        the ``FileGenerator`` to create this task. It is either an dictionary
        from the list of a ListObjects or the response from a HeadObject. It
        will only be filled if the task was generated from an S3 bucket.
    """
    def __init__(self, src, dest=None, compare_key=None, size=None,
                 last_update=None, src_type=None, dest_type=None,
                 operation_name=None, client=None, parameters=None,
                 source_client=None, is_stream=False,
                 associated_response_data=None):
        self.src = src
        self.src_type = src_type
        self.operation_name = operation_name
        self.client = client
        self.dest = dest
        self.dest_type = dest_type
        self.compare_key = compare_key
        self.size = size
        self.last_update = last_update
        # Usually inject ``parameters`` from ``BasicTask`` class.
        self.parameters = {}
        if parameters is not None:
            self.parameters = parameters
        self.source_client = source_client
        self.is_stream = is_stream
        self.associated_response_data = associated_response_data

    def set_size_from_s3(self):
        """
        This runs a ``HeadObject`` on the s3 object and sets the size.
        """
        bucket, key = find_bucket_key(self.src)
        params = {'Bucket': bucket,
                  'Key': key}
        RequestParamsMapper.map_head_object_params(params, self.parameters)
        response_data = self.client.head_object(**params)
        self.size = int(response_data['ContentLength'])

    def is_glacier_compatible(self):
        """Determines if a file info object is glacier compatible

        Operations will fail if the S3 object has a storage class of GLACIER
        and it involves copying from S3 to S3, downloading from S3, or moving
        where S3 is the source (the delete will actually succeed, but we do
        not want fail to transfer the file and then successfully delete it).

        :returns: True if the FileInfo's operation will not fail because the
            operation is on a glacier object. False if it will fail.
        """
        if self._is_glacier_object(self.associated_response_data):
            if self.operation_name in ['copy', 'download']:
                return False
            elif self.operation_name == 'move':
                if self.src_type == 's3':
                    return False
        return True

    def _is_glacier_object(self, response_data):
        if response_data:
            if response_data.get('StorageClass') == 'GLACIER' and \
                    not self._is_restored(response_data):
                return True
        return False

    def _is_restored(self, response_data):
        # Returns True is this is a glacier object that has been
        # restored back to S3.
        # 'Restore' looks like: 'ongoing-request="false", expiry-date="..."'
        return 'ongoing-request="false"' in response_data.get('Restore', '')

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
        self._inject_content_type(params)
        RequestParamsMapper.map_put_object_params(params, self.parameters)
        response_data = self.client.put_object(**params)

    def _inject_content_type(self, params):
        if not self.parameters['guess_mime_type']:
            return
        filename = self.src
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
        RequestParamsMapper.map_get_object_params(params, self.parameters)
        response_data = self.client.get_object(**params)
        save_file(self.dest, response_data, self.last_update,
                  self.is_stream)

    def copy(self):
        """
        Copies a object in s3 to another location in s3.
        """
        source_bucket, source_key = find_bucket_key(self.src)
        copy_source = {'Bucket': source_bucket, 'Key': source_key}
        bucket, key = find_bucket_key(self.dest)
        params = {'Bucket': bucket,
                  'CopySource': copy_source, 'Key': key}
        self._inject_content_type(params)
        RequestParamsMapper.map_copy_object_params(params, self.parameters)
        response_data = self.client.copy_object(**params)

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
        self._inject_content_type(params)
        RequestParamsMapper.map_create_multipart_upload_params(
            params, self.parameters)
        response_data = self.client.create_multipart_upload(**params)
        upload_id = response_data['UploadId']
        return upload_id

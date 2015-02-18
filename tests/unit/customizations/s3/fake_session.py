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
import hashlib
from operator import itemgetter
from botocore.vendored import requests
from awscli.compat import six
from six import text_type
from six import StringIO
from io import BytesIO

from mock import MagicMock, Mock

from awscli.customizations.s3.filegenerator import find_bucket_key


class FakeSession(object):
    """
    This class drives the operations for the unit tests for the plugin by
    providing an emulation of botocore's session module.  It is by no
    means a complete emulation of the session module.  The class also
    keeps track of dictionary that tracks an emulated state of s3.
    This feature allows the unit tests to preform commands on the
    emulated s3 profile and actually affect the emulated s3 profile
    without ever affecting an actual s3 profile or contacting s3.

    :var self.s3: This holds the current state of the emulated s3
        profile.  The variable is ordered such that the top level keys are
        bucket names. Each bucket name is a key to a dictionary of
        s3 objects.  The key's of the s3 objects are keys to another
        dictionary of relevant info about the object like its data,
        last modified time, size, and etag.
    :type self.s3: Dictionary. A sample form of the dictionary with
        a single object and bucket is
        {'mybucket': {'mykey': {'Body': "This is a test.",
                                'Size': 15,
                                'LastModified': '2013-07-15T17:03:43.000Z',
                                'ETag': 'ad35657fshafq4tg46'}}}
    :var self.service:  This is a mock serice to emulate botocore's
        session module

    :param md5_error: If true, some operations will raise an exception
        signaling the md5's do not match
    :param connection_error: If true, some operations will raise an exception
        signalling that there was a connection_error.
    """
    def __init__(self, md5_error=False, connection_error=False):
        self.s3 = {}
        self.service = FakeService(self)
        self.md5_error = md5_error
        self.connection_error = connection_error

    def get_config(self):
        return {'region': 'us-west-2'}

    def get_service(self, service='s3'):
        return self.service

    def emit(self, *args, **kwargs):
        pass

    def emit_first_non_none_response(self, *args, **kwargs):
        pass

    def register(self, name, handler, unique_id=None,
                 unique_id_uses_call=False):
        pass

    def unregister(self, name, handler, unique_id=None,
                   unique_id_uses_call=False):
        pass


class FakeService(object):
    """
    This class is an emulation of botocore's service module.
    It only includes the functions necessary to mock the service
    module in the unit tests.
    """
    def __init__(self, session):
        self.session = session

    def get_endpoint(self, region_name, endpoint_url=None, verify=None):
        endpoint = Mock()
        endpoint.region_name = region_name
        endpoint.endpoint_url = endpoint_url
        endpoint.verify = verify
        return endpoint

    def get_operation(self, name):
        return FakeOperation(name, self.session)


class FakeOperation(object):

    def __init__(self, name, session):
        """
        This class preforms the actual commands a session's s3.
        The only operations will raise errors when specified are
        PutObject, UploadPart, and GetObject.
        :param name: The name of the operation being preformed.
        """
        self.name = name
        self.session = session

    def call(self, *args, **kwargs):
        """
        This function preforms the call method of an operation.
        :returns: An emulated response data and emulated http_response
            from the operations preformed on s3.
        """
        op_dict = {'PutObject': self.put_object,
                   'CreateBucket': self.create_bucket,
                   'DeleteObject': self.delete_object,
                   'DeleteBucket': self.delete_bucket,
                   'ListObjects': self.list_objects,
                   'ListBuckets': self.list_buckets,
                   'CreateMultipartUpload': self.create_multi_upload,
                   'UploadPart': self.upload_part,
                   'CompleteMultipartUpload': self.complete_multi_upload,
                   'CopyObject': self.copy_object,
                   'GetObject': self.get_object,
                   'HeadObject': self.head_object,
                   'AbortMultipartUpload': self.abort_multi_upload}
        return op_dict[self.name](kwargs)

    def paginate(self, *args, **kwargs):
        """
        This function is exactly the same as the call() method however
        it yields the emulated data response and emulated http_response.
        """
        op_dict = {'ListObjects': self.list_objects}
        yield op_dict[self.name](kwargs)

    def put_object(self, kwargs):
        """
        This function puts an object into a session's s3.  It calculates
        the md5 of the body sent to the operation object and stores it both
        in s3 and the returned emulated http response object.  If the
        specified bucket does not exist it will send an error message in the
        response data.  If the object's session has been flagged to raise
        an exception, the first object(s) will raise the error or cause
        an error to be raised and flip the session's flag no longer allowing
        any other objects using the session to raise that exception.  The
        LastModified time assigned to the object is uniform and arbitrary.
        """
        bucket = kwargs['bucket']
        response_data = {}
        etag = ''
        if bucket in self.session.s3:
            key = kwargs['key']
            content = {}
            body = ''
            if 'body' in kwargs:
                body = kwargs['body']
                if isinstance(body, StringIO):
                    body = body.getvalue()
                if hasattr(body, 'read'):
                    body = body.read()
                elif not isinstance(body, bytearray):
                    body = body.encode('utf-8')
                content['Body'] = body
                m = hashlib.md5()
                m.update(body)
                etag = m.hexdigest()
            content['Size'] = len(body)
            content['LastModified'] = '2013-07-15T17:03:43.000Z'
            content['ETag'] = '"%s"' % etag
            if 'content_type' in kwargs:
                content['ContentType'] = kwargs['content_type']
            if key in self.session.s3[bucket]:
                self.session.s3[bucket][key].update(content)
            else:
                self.session.s3[bucket][key] = content
        else:
            response_data['Error'] = {'Message': 'Bucket does not exist'}
        if self.session.md5_error:
            etag = "dsffsdg"  # This etag should always raise an exception
            self.session.md5_error = False
        elif self.session.connection_error:
            self.session.connection_error = False
            raise requests.ConnectionError()
        response_data['ETag'] = '"%s"' % etag
        return FakeHttp(), response_data

    def create_bucket(self, kwargs):
        """
        This operation creates a bucket.  It sends an error message if the
        bucket already exists
        """
        bucket = kwargs['bucket']
        response_data = {}
        etag = ''
        if bucket not in self.session.s3:
            self.session.s3[bucket] = {}
        else:
            response_data['Errors'] = [{'Message': 'Bucket already exists'}]
        response_data['ETag'] = '"%s"' % etag
        return FakeHttp(), response_data

    def delete_object(self, kwargs):
        """
        This operation deletes an s3 object.  It sends an error message if
        the sprecified bucket does not exist.
        """
        bucket = kwargs['bucket']
        key = kwargs['key']
        response_data = {}
        etag = ''
        if bucket in self.session.s3:
            if key in self.session.s3[bucket]:
                self.session.s3[bucket].pop(key)
        else:
            response_data['Errors'] = [{'Message': 'Bucket does not exist'}]
        response_data['ETag'] = '"%s"' % etag
        return FakeHttp(), response_data

    def copy_object(self, kwargs):
        """
        This operation copies one s3 object to another location in s3.
        If either the bucket of the source or the destination does not
        exist, an error message will be sent stating that the bucket does
        not exist.
        """
        bucket = kwargs['bucket']
        key = kwargs['key']
        copy_source = kwargs['copy_source']
        src_bucket, src_key = find_bucket_key(copy_source)
        if not isinstance(src_key, text_type) and hasattr(src_key, 'decode'):
            src_key = src_key.decode('utf-8')
        response_data = {}
        etag = ''
        if bucket in self.session.s3 or src_bucket in self.session.s3:
            src = self.session.s3[src_bucket][src_key]
            self.session.s3[bucket][key] = src
        else:
            response_data['Errors'] = [{'Message': 'Bucket does not exist'}]
        response_data['ETag'] = '"%s"' % etag
        return FakeHttp(), response_data

    def get_object(self, kwargs):
        """
        This operation gets an object from s3.  It retrieves the body of
        the object or a part of the body specified by a range variable.
        A MagicMock() class is used to transfer the body allowing it to
        be read by a read() operation.  The etags no matter if it is
        a multipart download or not is invalid as it will have a dash
        in the etags.  So it is never compared during download.  If the
        session's connection_error flag is set, it will raise a
        ConnectionError and reset the flag to False.
        """
        bucket = kwargs['bucket']
        key = kwargs['key']
        response_data = {}
        etag = ''
        if bucket in self.session.s3:
            body = self.session.s3[bucket][key]['Body']
            if 'range' in kwargs:
                str_range = kwargs['range']
                str_range = str_range[6:]
                range_components = str_range.split('-')
                beginning = range_components[0]
                end = range_components[1]
                if end == '':
                    body = body[int(beginning):]
                else:
                    body = body[int(beginning):(int(end) + 1)]
            mock_response = BytesIO(body)
            mock_response.set_socket_timeout = Mock()
            response_data['Body'] = mock_response
            etag = self.session.s3[bucket][key]['ETag']
            response_data['ETag'] = etag + '--'
        else:
            response_data['Errors'] = [{'Message': 'Bucket does not exist'}]
        if self.session.connection_error:
            self.session.connection_error = False
            raise requests.ConnectionError
        return FakeHttp(), response_data

    def delete_bucket(self, kwargs):
        """
        This operation deletes an s3 bucket.  If the bucket does not
        exist or is not empty it will send an error message.
        """
        bucket = kwargs['bucket']
        response_data = {}
        etag = ''
        if bucket in self.session.s3:
            if not self.session.s3[bucket]:
                self.session.s3.pop(bucket)
            else:
                response_data['Error'] = {'Message': 'Bucket not empty'}
        else:
            response_data['Error'] = {'Message': 'Bucket does not exist'}
        response_data['ETag'] = '"%s"' % etag
        return FakeHttp(), response_data

    def list_buckets(self, kwargs):
        """
        This function returns the buckets in the session's s3.
        """
        response_data = {}
        etag = ''
        response_data['Buckets'] = []
        for bucket in self.session.s3.keys():
            bucket_dict = {}
            bucket_dict['Name'] = bucket
            response_data['Buckets'].append(bucket_dict)
        if self.session.s3.keys():
            response_data['Contents'] = sorted(response_data['Buckets'],
                                               key=lambda k: k['Name'])
        response_data['ETag'] = '"%s"' % etag
        return FakeHttp(), response_data

    def list_objects(self, kwargs):
        """
        This function returns the objects specified by a bucket and prefix.
        In the response data it includes the size and last modified time.
        """
        bucket = kwargs['bucket']
        prefix = ''
        if 'prefix' in kwargs:
            prefix = kwargs['prefix']
        response_data = {}
        etag = ''
        delimiter = ''
        if 'delimiter' in kwargs:
            delimiter = kwargs['delimiter']
            response_data['CommonPrefixes'] = []
        response_data['Contents'] = []
        objects = self.session.s3[bucket]
        for key in objects.keys():
            if key.startswith(prefix):
                key_dict = {}
                key_dict['Key'] = key
                size = objects[key]['Size']
                key_dict['Size'] = size
                key_dict['LastModified'] = objects[key]['LastModified']
                if key.endswith('/') and size == 0 and delimiter:
                    prefix_dict = {}
                    prefix_dict['Prefix'] = key
                    response_data['CommonPrefixes'].append(prefix_dict)
                response_data['Contents'].append(key_dict)
        response_data['Contents'] = sorted(response_data['Contents'],
                                           key=lambda k: k['Key'])
        contents = response_data.get('Contents', None)
        if not contents and contents is not None:
            response_data.pop('Contents')
        common_prefixes = response_data.get('CommonPrefixes', None)
        if not common_prefixes and common_prefixes is not None:
            response_data.pop('CommonPrefixes')
        response_data['ETag'] = '"%s"' % etag
        return FakeHttp(), response_data

    def head_object(self, kwargs):
        bucket = kwargs['bucket']
        key = kwargs['key']
        response_data = {}
        etag = ''
        if bucket not in self.session.s3 or key not in self.session.s3[bucket]:
            return FakeHttp(404), {}
        key = self.session.s3[bucket][key]
        response_data['ContentLength'] = str(key['Size'])
        response_data['LastModified'] = key['LastModified']
        return FakeHttp(), response_data

    def create_multi_upload(self, kwargs):
        """
        A dummy function that returns an arbitrary upload id necessary
        for a multipart upload.
        """
        bucket = kwargs['bucket']
        if bucket in self.session.s3:
            content = {}
            key = kwargs['key']
            content['ContentType'] = kwargs.get('content_type')
            self.session.s3[bucket][key] = content
        return FakeHttp(), {'UploadId': 'upload_id'}

    def upload_part(self, kwargs):
        """
        This function is exaclty the same as PutObject because
        it is used to check parts are properly read and uoloaded
        by checking the etags
        """
        return self.put_object(kwargs)

    def complete_multi_upload(self, kwargs):
        """
        A function that acts as a mock function for
        CompleteMultipartUpload calls
        """
        return FakeHttp(), {}

    def abort_multi_upload(self, kwargs):
        """
        A function that acts as a mock function for
        CompleteMultipartUpload calls
        """
        return FakeHttp(), {}


class FakeHttp(object):
    """
    This class emulates the http responses from an operation's
    call method.  The http responses are only used to retrieve
    etag's.  So only formatted etag's are included in this class.
    """
    def __init__(self, status_code=200):
        self.status_code = status_code

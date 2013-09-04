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
import botocore.session

class OperationException(Exception):
    """
    An exception to be thrown when service operations fail. The exception
    contains a link to the operation, the arguments that were used to
    invoke the operation, the HTTP response object and response data.
    """
    def __init__(self, operation, args=None, res=None, data=None):
        super(OperationException, self).__init__()

        self.operation = operation
        self.args = args
        self.res = res
        self.data = data


class OperationProxy(object):
    """
    A callable proxy for a service operation. This object essentially
    acts like a function where the keyword arguments are passed as
    arguments to the operation. This is used along with the Service
    class below to provide a simple interface to Botocore operations.

    Botocore usually returns two objects from an operation: the HTTP
    response and parsed data. Calling an OperationProxy instance will
    return the parsed data, or raise an OperationException if the
    HTTP response code is not successful (200, 201, etc).
    """
    def __init__(self, service, name, endpoint):
        self.service = service
        self.name = name
        self.endpoint = endpoint

        self._operation = service.get_operation(name)

    def __call__(self, **kwargs):
        res, data = self._operation.call(self.endpoint, **kwargs)

        if res.status_code < 200 or res.status_code > 300:
            raise OperationException(self, kwargs, res, data)

        return data


class Service(object):
    """
    An object to represent a Botocore service for a particular
    region/endpoint and session, which allows simple attribute
    access to operations.

        >>> s3 = Service('s3')
        >>> s3.CreateBucket(bucket='my-test-bucket')
        >>> data = s3.PutObject(bucket='my-test-bucket', key='test.txt',
                                body='Hello, world!')
        >>> print(data['ETag'])
        '828ef3fdfa96f00ad9f27c383fc9ac7f'

    An endpoint can be set in the constructor:

        >>> s3 = Service('s3', 'us-west-1')

    As can a specific endpoint URL:

       >>> s3 = Service('s3', {'endpoint_url': 'http://...'})

    A custom session can be used:

        >>> s3 = Service('s3', session=mysession)

    """
    def __init__(self, name, endpoint_args=None, session=None):
        self.name = name
        self.session = session or botocore.session.get_session()

        self._service = self.session.get_service(name)

        if endpoint_args is None:
            endpoint_args = {}
        elif not isinstance(endpoint_args, dict):
            endpoint_args = {'region_name': endpoint_args}

        self.endpoint = self._service.get_endpoint(**endpoint_args)

    def __getattr__(self, name):
        return OperationProxy(self._service, name, self.endpoint)

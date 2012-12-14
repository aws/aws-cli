# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
# Copyright 2012 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
from .endpoint import get_endpoint
from .base import get_service_data
from .operation import Operation


class Service(object):
    """
    A service, such as Elastic Compute Cloud (EC2).

    :ivar api_version: A string containing the API version this service
        is using.
    :ivar name: The full name of the service.
    :ivar service_name: The canonical name of the service.
    :ivar regions: A dict where each key is a region name and the
        optional value is an endpoint for that region.
    :ivar protocols: A list of protocols supported by the service.
    """

    def __init__(self, session, provider_name, service_name,
                 path='/', port=None):
        self.membered_lists = True
        self.__dict__.update(get_service_data(service_name, provider_name))
        self.session = session
        self.provider_name = provider_name
        self.path = path
        self.port = port
        self.cli_name = self.short_name
        self._operations_data = self.operations
        self.operations = []
        for operation_data in self._operations_data:
            op = Operation(self, operation_data)
            self.operations.append(op)
            setattr(self, op.py_name, op)

    def __repr__(self):
        return 'Service(%s)' % self.name

    @property
    def region_names(self):
        return self.regions.keys()

    def get_endpoint(self, region_name, is_secure=True, endpoint_url=None):
        """
        Return the Endpoint object for this service in a particular
        region.

        :type region_name: str
        :param region_name: The name of the region.

        :type is_secure: bool
        :param is_secure: True if you want the secure (HTTPS) endpoint.
        """
        if region_name not in self.regions:
            raise ValueError('Service: %s not available in region: %s' %
                             (self.service_name, region_name))
        endpoint_url = endpoint_url or self.regions[region_name]
        if endpoint_url is None:
            if is_secure:
                scheme = 'https'
            else:
                scheme = 'http'
            if scheme not in self.protocols:
                raise ValueError('Unsupported protocol: %s' % scheme)
            host = '%s.%s.amazonaws.com' % (self.short_name, region_name)
            endpoint_url = '%s://%s%s' % (scheme, host, self.path)
            if self.port:
                endpoint_url += ':%d' % self.port
        return get_endpoint(self, region_name, endpoint_url)

    def get_operation(self, operation_name):
        """
        Find an Operation object for a given operation_name.  The name
        provided can be the original camel case name, the Python name or
        the CLI name.

        :type operation_name: str
        :param operation_name: The name of the operation.
        """
        for operation in self.operations:
            op_names = (operation.name, operation.py_name, operation.cli_name)
            if operation_name in op_names:
                return operation
        return None


def get_service(session, service_name, provider_name='aws'):
    """
    Return a Service object for a given provider name and service name.

    :type service_name: str
    :param service_name: The name of the service.

    :type provider_name: str
    :param provider_name: The name of the provider.
    """
    return Service(session, provider_name, service_name)

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

# to enable detailed debugging from httplib layer
#import httplib
#httplib.HTTPConnection.debuglevel = 2

import logging
import requests
import auth
import credentials
import response
import operation
from . import user_agent

logger = logging.getLogger(__name__)


class Endpoint(object):
    """
    Represents an endpoint for a particular service in a specific
    region.  Only an endpoint can make requests.

    :ivar service: The Service object that describes this endpoints
        service.
    :ivar host: The fully qualified endpoint hostname.
    :ivar credentials: The credentials that will be used to authorize
        requests.
    """

    def __init__(self, service, region_name, host, profile=None):
        self.service = service
        self.region_name = region_name
        self.host = host
        self.profile = profile
        self.credentials = credentials.get_credentials(profile=profile)
        self.auth = auth.get_auth(self.service.authentication,
                                  credentials=self.credentials,
                                  service_name=self.service.short_name,
                                  region_name=region_name)
        self.operations = []
        for operation in self.service.operations:
            op = operation.Operation(self, operation)
            self.operations.append(op)
            setattr(self, op.py_name, op)

    def __repr__(self):
        return '%s(%s)' % (self.service.name, self.host)

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

    def make_request(self, params, list_marker=None):
        pass


class QueryEndpoint(Endpoint):
    """
    This class handles only AWS/Query style services.
    """

    def make_request(self, operation, params):
        """
        Send a request to the endpoint and parse the response
        and return it and long with the HTTP response object
        from requests.
        """
        logger.debug(params)
        http_response = requests.post(self.host, params=params,
                                      hooks={'args': self.auth.add_auth},
                                      headers={'User-Agent': user_agent()})
        r = response.Response(operation)
        http_response.encoding = 'utf-8'
        body = http_response.text.encode('utf=8')
        logger.debug(body)
        r.parse(body)
        return (http_response, r.get_value())


def get_endpoint(service, region_name, endpoint_url, profile=None):
    return QueryEndpoint(service, region_name, endpoint_url, profile)

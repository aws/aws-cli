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

import logging
import json
import requests
import botocore.auth
import botocore.response

logger = logging.getLogger(__name__)


class Endpoint(object):
    """
    Represents an endpoint for a particular service in a specific
    region.  Only an endpoint can make requests.

    :ivar service: The Service object that describes this endpoints
        service.
    :ivar host: The fully qualified endpoint hostname.
    :ivar session: The session object.
    """

    def __init__(self, service, region_name, host):
        self.service = service
        self.session = self.service.session
        self.region_name = region_name
        self.host = host
        self.auth = botocore.auth.get_auth(self.service.authentication,
                                           credentials=self.session.get_credentials(),
                                           service_name=self.service.short_name,
                                           region_name=region_name)

    def __repr__(self):
        return '%s(%s)' % (self.service.name, self.host)

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
        params['Action'] = operation.name
        params['Version'] = self.service.api_version
        user_agent = self.session.user_agent()
        http_response = requests.post(self.host, params=params,
                                      hooks={'args': self.auth.add_auth},
                                      headers={'User-Agent': user_agent})
        r = botocore.response.Response(operation)
        http_response.encoding = 'utf-8'
        body = http_response.text.encode('utf=8')
        logger.debug(body)
        r.parse(body)
        return (http_response, r.get_value())


class JSONEndpoint(Endpoint):
    """
    This class handles only AWS/JSON style services.
    """

    def make_request(self, operation, params):
        """
        Send a request to the endpoint and parse the response
        and return it and long with the HTTP response object
        from requests.
        """
        logger.debug(params)
        user_agent = self.session.user_agent()
        target = '%s.%s' % (self.service.service_name, operation.name)
        content_type = 'application/x-amz-json-1.1'
        data = json.dumps(params)
        http_response = requests.post(self.host, data=data,
                                      hooks={'args': self.auth.add_auth},
                                      headers={'User-Agent': user_agent,
                                               'X-Amz-Target': target,
                                               'Content-Type': content_type})
        http_response.encoding = 'utf-8'
        body = http_response.text.encode('utf=8')
        logger.debug(body)
        return (http_response, json.loads(body))


def get_endpoint(service, region_name, endpoint_url):
    if service.type == 'query':
        return QueryEndpoint(service, region_name, endpoint_url)
    if service.type == 'json':
        return JSONEndpoint(service, region_name, endpoint_url)
    raise exceptions.UnknownServiceStyle(service_style=service.type)

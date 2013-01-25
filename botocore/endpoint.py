# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import botocore.exceptions

try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

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
        self.verify = True
        if hasattr(self.service, 'signing_name'):
            signing_name = self.service.signing_name
        else:
            signing_name = self.service.endpoint_prefix
        self.auth = botocore.auth.get_auth(self.service.signature_version,
                                           credentials=self.session.get_credentials(),
                                           service_name=signing_name,
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
        logger.debug('SSL Verify: %s' % self.verify)
        params['Action'] = operation.name
        params['Version'] = self.service.api_version
        user_agent = self.session.user_agent()
        http_response = requests.post(self.host, params=params,
                                      hooks={'args': self.auth.add_auth},
                                      headers={'User-Agent': user_agent},
                                      verify=self.verify)
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
        logger.debug('SSL Verify: %s' % self.verify)
        user_agent = self.session.user_agent()
        target = '%s.%s' % (self.service.target_prefix, operation.name)
        content_type = 'application/x-amz-json-1.1'
        data = json.dumps(params)
        http_response = requests.post(self.host, data=data,
                                      hooks={'args': self.auth.add_auth},
                                      headers={'User-Agent': user_agent,
                                               'X-Amz-Target': target,
                                               'Content-Type': content_type},
                                      verify=self.verify)
        http_response.encoding = 'utf-8'
        body = http_response.text.encode('utf=8')
        logger.debug(body)
        return (http_response, json.loads(body))


class RestXMLEndpoint(Endpoint):

    def get_path_and_query_params(self, operation, params):
        uri = operation.http['uri']
        if '?' in uri:
            path, query_params = uri.split('?')
        else:
            path = uri
            query_params = ''
        logger.debug('path: %s' % path)
        logger.debug('query_params: %s' % query_params)
        path_components = []
        for pc in path.split('/'):
            if pc:
                pc = pc.format(**params['uri_params'])
            path_components.append(pc)
        path = '/'.join(path_components)
        query_param_components = {}
        for qpc in query_params.split('&'):
            if qpc:
                key_name, value_name = qpc.split('=')
                value_name = value_name.strip('{}')
                if value_name in params['uri_params']:
                    query_param_components[key_name] = params['uri_params'][value_name]
        logger.debug('path: %s' % path)
        logger.debug('query_params: %s' % query_param_components)
        return path, query_param_components

    def make_request(self, operation, params):
        """
        Send a request to the endpoint and parse the response
        and return it and long with the HTTP response object
        from requests.
        """
        logger.debug(params)
        logger.debug('SSL Verify: %s' % self.verify)
        user_agent = self.session.user_agent()
        request_method = getattr(requests, operation.http['method'].lower())
        path, query_params = self.get_path_and_query_params(operation, params)
        uri = urljoin(self.host, path)
        http_response = request_method(uri, params=query_params,
                                       hooks={'args': self.auth.add_auth},
                                       headers={'User-Agent': user_agent},
                                       verify=self.verify)
        r = botocore.response.Response(operation)
        http_response.encoding = 'utf-8'
        body = http_response.text.encode('utf=8')
        logger.debug(body)
        r.parse(body)
        return (http_response, r.get_value())


def get_endpoint(service, region_name, endpoint_url):
    if service.type == 'query':
        return QueryEndpoint(service, region_name, endpoint_url)
    if service.type == 'json':
        return JSONEndpoint(service, region_name, endpoint_url)
    if service.type == 'rest-xml':
        return RestXMLEndpoint(service, region_name, endpoint_url)
    raise botocore.exceptions.UnknownServiceStyle(service_style=service.type)

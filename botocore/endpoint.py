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
from requests.sessions import Session

import botocore.auth
import botocore.response
import botocore.exceptions
from botocore.awsrequest import AWSRequest

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

    def __init__(self, service, region_name, host, auth):
        self.service = service
        self.session = self.service.session
        self.region_name = region_name
        self.host = host
        self.verify = True
        self.auth = auth
        self.http_session = Session()

    def __repr__(self):
        return '%s(%s)' % (self.service.endpoint_prefix, self.host)

    def make_request(self, params, list_marker=None):
        raise NotImplementedError("make_request")

    def prepare_request(self, request):
        logger.debug('prepare_request')
        self.auth.add_auth(request=request)
        prepared_request = request.prepare()
        return prepared_request


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
        request = AWSRequest(method='POST', url=self.host,
                             data=params, headers={'User-Agent': user_agent})
        prepared_request = self.prepare_request(request)
        http_response = self.http_session.send(prepared_request,
                                               verify=self.verify,
                                               stream=operation.is_streaming())
        return botocore.response.get_response(operation, http_response)


class JSONEndpoint(Endpoint):
    """
    This class handles only AWS/JSON style services.
    """

    ResponseContentTypes = ['application/x-amz-json-1.1',
                            'application/json']

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
        json_version = '1.0'
        if hasattr(self.service, 'json_version'):
            json_version = str(self.service.json_version)
        content_type = 'application/x-amz-json-%s' % json_version
        content_encoding = 'amz-1.0'
        data = json.dumps(params)
        request = AWSRequest(method='POST', url=self.host,
                             data=data,
                             headers={'User-Agent': user_agent,
                                      'X-Amz-Target': target,
                                      'Content-Type': content_type,
                                      'Content-Encoding': content_encoding})
        prepared_request = self.prepare_request(request)
        http_response = self.http_session.send(prepared_request,
                                               verify=self.verify,
                                               stream=operation.is_streaming())
        return botocore.response.get_response(operation, http_response)


class RestEndpoint(Endpoint):

    def build_uri(self, operation, params):
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
        query_param_components = []
        for qpc in query_params.split('&'):
            if qpc:
                if '=' in qpc:
                    key_name, value_name = qpc.split('=')
                else:
                    key_name = qpc
                    value_name = None
                if value_name:
                    value_name = value_name.strip('{}')
                    if value_name in params['uri_params']:
                        value = params['uri_params'][value_name]
                        query_param_components.append('%s=%s' % (key_name,
                                                                 value))
                else:
                    query_param_components.append(key_name)
        query_params = '&'.join(query_param_components)
        logger.debug('path: %s' % path)
        logger.debug('query_params: %s' % query_params)
        return path + '?' + query_params

    def make_request(self, operation, params):
        """
        Send a request to the endpoint and parse the response
        and return it and long with the HTTP response object
        from requests.
        """
        logger.debug(params)
        logger.debug('SSL Verify: %s' % self.verify)
        user_agent = self.session.user_agent()
        params['headers']['User-Agent'] = user_agent
        uri = self.build_uri(operation, params)
        uri = urljoin(self.host, uri)
        request = AWSRequest(method=operation.http['method'],
                             url=uri, headers=params['headers'],
                             data=params['payload'])
        prepared_request = self.prepare_request(request)
        http_response = self.http_session.send(prepared_request,
                                               verify=self.verify,
                                               stream=operation.is_streaming())
        return botocore.response.get_response(operation, http_response)


def get_endpoint(service, region_name, endpoint_url):
    service_to_endpoint = {
        'query': QueryEndpoint,
        'json': JSONEndpoint,
        'rest-xml': RestEndpoint,
        'rest-json': RestEndpoint,
    }
    service_type = service.type
    if service_type not in service_to_endpoint:
        raise botocore.exceptions.UnknownServiceStyle(
            service_style=service.type)
    cls = service_to_endpoint.get(service_type)
    if cls is None:
        raise NotImplementedError("%s service type is not yet implemented" %
                                  service_type)
    service_name = getattr(service, 'signing_name', service.endpoint_prefix)
    auth = botocore.auth.get_auth(service.signature_version,
                                  credentials=service.session.get_credentials(),
                                  service_name=service_name,
                                  region_name=region_name)
    return cls(service, region_name, endpoint_url, auth=auth)

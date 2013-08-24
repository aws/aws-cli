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
import time

from requests.sessions import Session
from requests.utils import get_environ_proxies
import six

import botocore.response
import botocore.exceptions
from botocore.auth import AUTH_TYPE_MAPS
from botocore.exceptions import UnknownSignatureVersionError
from botocore.awsrequest import AWSRequest
from botocore.compat import urljoin, json, quote


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

    def __init__(self, service, region_name, host, auth, proxies=None):
        self.service = service
        self.session = self.service.session
        self.region_name = region_name
        self.host = host
        self.verify = True
        self.auth = auth
        if proxies is None:
            proxies = {}
        self.proxies = proxies
        self.http_session = Session()

    def __repr__(self):
        return '%s(%s)' % (self.service.endpoint_prefix, self.host)

    def make_request(self, operation, params):
        logger.debug("Making request for %s (verify_ssl=%s) with params: %s",
                     operation, self.verify, params)
        request = self._create_request_object(operation, params)
        prepared_request = self.prepare_request(request)
        return self._send_request(prepared_request, operation)

    def _create_request_object(self, operation, params):
        raise NotImplementedError('_create_request_object')

    def prepare_request(self, request):
        if self.auth is not None:
            event = self.session.create_event('before-auth',
                                              self.service.endpoint_prefix)
            self.session.emit(event, endpoint=self,
                              request=request, auth=self.auth)
            self.auth.add_auth(request=request)
        prepared_request = request.prepare()
        return prepared_request

    def _send_request(self, request, operation):
        attempts = 1
        response, exception = self._get_response(request, operation, attempts)
        while self._needs_retry(attempts, operation, response, exception):
            attempts += 1
            response, exception = self._get_response(request, operation,
                                                     attempts)
        return response

    def _get_response(self, request, operation, attempts):
        try:
            logger.debug("Sending http request: %s", request)
            http_response = self.http_session.send(
                request, verify=self.verify,
                stream=operation.is_streaming(),
                proxies=self.proxies)
        except Exception as e:
            return (None, e)
        # This returns the http_response and the parsed_data.
        return (botocore.response.get_response(self.session, operation,
                                               http_response), None)

    def _needs_retry(self, attempts, operation, response=None,
                     caught_exception=None):
        event = self.session.create_event(
            'needs-retry', self.service.endpoint_prefix, operation.name)
        handler_response = self.session.emit_first_non_none_response(
            event, response=response, endpoint=self,
            operation=operation, attempts=attempts,
            caught_exception=caught_exception)
        if handler_response is None:
            return False
        else:
            # Request needs to be retried, and we need to sleep
            # for the specified number of times.
            logger.debug("Response received to retry, sleeping for "
                         "%s seconds", handler_response)
            time.sleep(handler_response)
            return True


class QueryEndpoint(Endpoint):
    """
    This class handles only AWS/Query style services.
    """

    def _create_request_object(self, operation, params):
        params['Action'] = operation.name
        params['Version'] = self.service.api_version
        user_agent = self.session.user_agent()
        request = AWSRequest(method='POST', url=self.host,
                             data=params, headers={'User-Agent': user_agent})
        return request


class JSONEndpoint(Endpoint):
    """
    This class handles only AWS/JSON style services.
    """

    ResponseContentTypes = ['application/x-amz-json-1.1',
                            'application/json']

    def _create_request_object(self, operation, params):
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
        return request


class RestEndpoint(Endpoint):

    def build_uri(self, operation, params):
        logger.debug('Building URI for rest endpoint.')
        uri = operation.http['uri']
        if '?' in uri:
            path, query_params = uri.split('?')
        else:
            path = uri
            query_params = ''
        logger.debug('Templated URI path: %s', path)
        logger.debug('Templated URI query_params: %s', query_params)
        path_components = []
        for pc in path.split('/'):
            if pc:
                pc = six.text_type(pc).format(**params['uri_params'])
            path_components.append(pc)
        path = quote('/'.join(path_components).encode('utf-8'), safe='/~')
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
        logger.debug('Rendered path: %s', path)
        logger.debug('Rendered query_params: %s', query_params)
        return path + '?' + query_params

    def _create_request_object(self, operation, params):
        user_agent = self.session.user_agent()
        params['headers']['User-Agent'] = user_agent
        uri = self.build_uri(operation, params)
        uri = urljoin(self.host, uri)
        payload = None
        if params['payload']:
            payload = params['payload'].getvalue()
        if payload is None:
            request = AWSRequest(method=operation.http['method'],
                                 url=uri, headers=params['headers'])
        else:
            request = AWSRequest(method=operation.http['method'],
                                 url=uri, headers=params['headers'],
                                 data=payload)
        return request


def _get_proxies(url):
    # We could also support getting proxies from a config file,
    # but for now proxy support is taken from the environment.
    return get_environ_proxies(url)


def get_endpoint(service, region_name, endpoint_url):
    cls = SERVICE_TO_ENDPOINT.get(service.type)
    if cls is None:
        raise botocore.exceptions.UnknownServiceStyle(
            service_style=service.type)
    service_name = getattr(service, 'signing_name', service.endpoint_prefix)
    auth = None
    if hasattr(service, 'signature_version'):
        auth = _get_auth(service.signature_version,
                         credentials=service.session.get_credentials(),
                         service_name=service_name,
                         region_name=region_name)
    proxies = _get_proxies(endpoint_url)
    return cls(service, region_name, endpoint_url, auth=auth, proxies=proxies)


def _get_auth(signature_version, credentials, service_name, region_name):
    cls = AUTH_TYPE_MAPS.get(signature_version)
    if cls is None:
        raise UnknownSignatureVersionError(signature_version=signature_version)
    else:
        return cls(credentials=credentials,
                   service_name=service_name,
                   region_name=region_name)


SERVICE_TO_ENDPOINT = {
    'query': QueryEndpoint,
    'json': JSONEndpoint,
    'rest-xml': RestEndpoint,
    'rest-json': RestEndpoint,
}

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

import sys
import logging

LOG = logging.getLogger(__name__)


class ClientError(Exception):
    pass


class ServerError(Exception):
    pass


class ErrorHandler(object):
    """
    This class is responsible for handling any HTTP errors that occur
    when a service operation is called.  It is registered for the
    ``after-call`` event and will have the opportunity to inspect
    all operation calls.  If the HTTP response contains an error
    ``status_code`` an appropriate error message will be printed and
    the handler will short-circuit all further processing by exiting
    with an appropriate error code.
    """

    def __call__(self, http_response, parsed, operation, **kwargs):
        LOG.debug('HTTP Response Code: %d', http_response.status_code)
        if http_response.status_code >= 500:
            code, message = self._get_error_code_and_message(parsed)
            msg = "A server error ({error_code}) occurred: {error_message}"
            msg = msg.format(error_code=code, error_message=message)
            raise ServerError(msg)
        if http_response.status_code >= 400 or http_response.status_code == 301:
            code, message = self._get_error_code_and_message(parsed)
            msg = "A client error ({error_code}) occurred: {error_message}"
            msg = msg.format(error_code=code, error_message=message)
            raise ClientError(msg)
        return 0

    def _get_error_code_and_message(self, response):
        code = 'Unknown'
        message = 'Unknown'
        if 'Errors' in response:
            if isinstance(response['Errors'], list):
                error = response['Errors'][-1]
                if 'Code' in error:
                    code = error['Code']
                elif 'Type' in error:
                    code = error['Type']
                if 'Message' in error:
                    message = error['Message']
        return (code, message)

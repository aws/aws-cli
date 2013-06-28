# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Builtin event handlers.

This module contains builtin handlers for events emitted by botocore.
"""

import base64
import json
import hashlib
import logging
import re

import six

from botocore.compat import urlsplit, urlunsplit, unquote
from botocore import retryhandler


logger = logging.getLogger(__name__)
LabelRE = re.compile('[a-z0-9][a-z0-9\-]*[a-z0-9]')


def decode_console_output(event_name, shape, value, **kwargs):
    try:
        value = base64.b64decode(six.b(value)).decode('utf-8')
    except:
        logger.debug('error decoding base64', exc_info=True)
    return value


def decode_quoted_jsondoc(event_name, shape, value, **kwargs):
    try:
        value = json.loads(unquote(value))
    except:
        logger.debug('error loading quoted JSON', exc_info=True)
    return value


def decode_jsondoc(event_name, shape, value, **kwargs):
    try:
        value = json.loads(value)
    except:
        logger.debug('error loading JSON', exc_info=True)
    return value


def calculate_md5(event_name, params, **kwargs):
    if params['payload'] and not 'Content-MD5' in params['headers']:
        md5 = hashlib.md5()
        md5.update(params['payload'])
        params['headers']['Content-MD5'] = base64.b64encode(md5.digest())


def check_dns_name(bucket_name):
    """
    Check to see if the ``bucket_name`` complies with the
    restricted DNS naming conventions necessary to allow
    access via virtual-hosting style.
    """
    n = len(bucket_name)
    if n < 3 or n > 63:
        # Wrong length
        return False
    labels = bucket_name.split('.')
    if len(labels) == 4:
        # Must make sure this is not formatted like an IP address
        if all([(d.isdigit() and int(d)<256) for d in labels]):
            return False
    for label in bucket_name.split('.'):
        if len(label) == 0:
            # Must be two '.' in a row
            return False
        if len(label) == 1:
            if label.isalnum():
                continue
            # Any single character label must be alphanumeric
            return False
        match = LabelRE.match(label)
        if match is None or match.end() != len(label):
            return False
    return True


def fix_s3_host(event_name, endpoint, request, auth, **kwargs):
    """
    This handler looks at S3 requests just before they are signed.
    If there is a bucket name on the path (true for everything except
    ListAllBuckets) it checks to see if that bucket name conforms to
    the DNS naming conventions.  If it does, it alters the request to
    use ``virtual hosting`` style addressing rather than ``path-style``
    addressing.  This allows us to avoid 301 redirects for all
    bucket names that can be CNAME'd.
    """
    logger.debug('fix_s3_host: uri=%s' % request.url)
    parts = urlsplit(request.url)
    auth.auth_path = parts.path
    path_parts = parts.path.split('/')
    logger.debug('path_parts: %s' % path_parts)
    if len(path_parts) > 1:
        # If the operation is on a bucket, the auth_path must be
        # terminated with a '/' character.
        if len(path_parts) == 2:
            if auth.auth_path[-1] != '/':
                auth.auth_path += '/'
        bucket_name = path_parts[1]
        if check_dns_name(bucket_name):
            path_parts.remove(bucket_name)
            host = bucket_name + '.' + endpoint.service.global_endpoint
            new_tuple = (parts.scheme, host, '/'.join(path_parts),
                         parts.query, '')
            new_uri = urlunsplit(new_tuple)
            request.url = new_uri
            logger.debug('fix_s3_host: new uri=%s' % new_uri)


def register_retries_for_service(service, **kwargs):
    if not hasattr(service, 'retry'):
        return
    config = service.retry
    session = service.session
    handler = retryhandler.create_retry_handler(config)
    unique_id = 'retry-config-%s' % service.endpoint_prefix
    session.register('needs-retry.%s' % service.endpoint_prefix,
                     handler, unique_id=unique_id)
    _register_for_operations(config, session,
                             service_name=service.endpoint_prefix)


def _register_for_operations(config, session, service_name):
    # There's certainly a tradeoff for registering the retry config
    # for the operations when the service is created.  In practice,
    # there aren't a whole lot of per operation retry configs so
    # this is ok for now.
    for key in config:
        if key == '__default__':
            continue
        handler = retryhandler.create_retry_handler(config, key)
        unique_id = 'retry-config-%s-%s' % (service_name, key)
        session.register('needs-retry.%s.%s' % (service_name, key),
                         handler, unique_id=unique_id)


# This is a list of (event_name, handler).
# When a Session is created, everything in this list will be
# automatically registered with that Session.
BUILTIN_HANDLERS = [
    ('after-parsed.ec2.GetConsoleOutput.String.Output',
     decode_console_output),
    ('after-parsed.iam.*.policyDocumentType.*',
     decode_quoted_jsondoc),
    ('after-parsed.cloudformation.*.TemplateBody.TemplateBody',
     decode_jsondoc),
    ('before-call.s3.PutBucketTagging', calculate_md5),
    ('before-auth.s3', fix_s3_host),
    ('service-created', register_retries_for_service),
]

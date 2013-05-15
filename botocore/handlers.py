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
import six
from botocore.compat import unquote

logger = logging.getLogger(__name__)


def decode_console_output(event_name, shape, value, **kwargs):
    try:
        value = base64.b64decode(value).decode('utf-8')
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

# This is a list of (event_name, handler).
# When a Session is created, everything in this list will be
# automatically registered with that Session.
BUILTIN_HANDLERS = [
    ('after-parsed.ec2.GetConsoleOutput.String.Output',
     decode_console_output),
    ('after-parsed.iam.*.policyDocumentType.PolicyDocument',
     decode_quoted_jsondoc),
    ('after-parsed.cloudformation.*.TemplateBody.TemplateBody',
     decode_jsondoc),
    ('before-call.s3.PutBucketTagging', calculate_md5)
]

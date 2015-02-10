#!/usr/bin/env python
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import logging
import os

from botocore.vendored import requests
from awscli.compat import six

from awscli.compat import compat_open


logger = logging.getLogger(__name__)

# These are special cased arguments that do _not_ get the
# special param file processing.  This is typically because it
# refers to an actual URI of some sort and we don't want to actually
# download the content (i.e TemplateURL in cloudformation).
PARAMFILE_DISABLED = set([
    'cloudformation.create-stack.template-url',
    'cloudformation.update-stack.template-url',
    'cloudformation.validate-template.template-url',
    'cloudformation.estimate-template-cost.template-url',

    'cloudformation.create-stack.stack-policy-url',
    'cloudformation.update-stack.stack-policy-url',
    'cloudformation.set-stack-policy.stack-policy-url',

    # We will want to change the event name to ``s3`` as opposed to
    # custom in the near future along with ``s3`` to ``s3api``.
    'custom.cp.website-redirect',
    'custom.mv.website-redirect',
    'custom.sync.website-redirect',

    'sqs.add-permission.queue-url',
    'sqs.change-message-visibility.queue-url',
    'sqs.change-message-visibility-batch.queue-url',
    'sqs.delete-message.queue-url',
    'sqs.delete-message-batch.queue-url',
    'sqs.delete-queue.queue-url',
    'sqs.get-queue-attributes.queue-url',
    'sqs.list-dead-letter-source-queues.queue-url',
    'sqs.receive-message.queue-url',
    'sqs.remove-permission.queue-url',
    'sqs.send-message.queue-url',
    'sqs.send-message-batch.queue-url',
    'sqs.set-queue-attributes.queue-url',
    'sqs.purge-queue.queue-url',

    's3.copy-object.website-redirect-location',
    's3.create-multipart-upload.website-redirect-location',
    's3.put-object.website-redirect-location',

    # Double check that this has been renamed!
    'sns.subscribe.notification-endpoint',
])


class ResourceLoadingError(Exception):
    pass


def get_paramfile(path):
    """
    It is possible to pass parameters to operations by referring
    to files or URI's.  If such a reference is detected, this
    function attempts to retrieve the data from the file or URI
    and returns it.  If there are any errors or if the ``path``
    does not appear to refer to a file or URI, a ``None`` is
    returned.
    """
    data = None
    if isinstance(path, six.string_types):
        for prefix in PrefixMap:
            if path.startswith(prefix):
                kwargs = KwargsMap.get(prefix, {})
                data = PrefixMap[prefix](prefix, path, **kwargs)
    return data


def get_file(prefix, path, mode):
    file_path = path[len(prefix):]
    file_path = os.path.expanduser(file_path)
    file_path = os.path.expandvars(file_path)
    if not os.path.isfile(file_path):
        raise ResourceLoadingError("file does not exist: %s" % file_path)
    try:
        with compat_open(file_path, mode) as f:
            return f.read()
    except (OSError, IOError) as e:
        raise ResourceLoadingError('Unable to load paramfile %s: %s' % (
            path, e))


def get_uri(prefix, uri):
    try:
        r = requests.get(uri)
        if r.status_code == 200:
            return r.text
        else:
            raise ResourceLoadingError(
                "received non 200 status code of %s" % (
                    r.status_code))
    except Exception as e:
        raise ResourceLoadingError('Unable to retrieve %s: %s' % (uri, e))


PrefixMap = {'file://': get_file,
             'fileb://': get_file,
             'http://': get_uri,
             'https://': get_uri}

KwargsMap = {'file://': {'mode': 'r'},
             'fileb://': {'mode': 'rb'},
             'http://': {},
             'https://': {}}

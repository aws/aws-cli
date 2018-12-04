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
    'apigateway.put-integration.uri',
    'cloudformation.create-stack.template-url',
    'cloudformation.update-stack.template-url',
    'cloudformation.create-change-set.template-url',
    'cloudformation.validate-template.template-url',
    'cloudformation.estimate-template-cost.template-url',

    'cloudformation.create-stack.stack-policy-url',
    'cloudformation.update-stack.stack-policy-url',
    'cloudformation.set-stack-policy.stack-policy-url',

    'cloudformation.update-stack.stack-policy-during-update-url',
    # We will want to change the event name to ``s3`` as opposed to
    # custom in the near future along with ``s3`` to ``s3api``.
    'custom.cp.website-redirect',
    'custom.mv.website-redirect',
    'custom.sync.website-redirect',

    'iam.create-open-id-connect-provider.url',

    'machinelearning.predict.predict-endpoint',

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
    """Load parameter based on a resource URI.

    It is possible to pass parameters to operations by referring
    to files or URI's.  If such a reference is detected, this
    function attempts to retrieve the data from the file or URI
    and returns it.  If there are any errors or if the ``path``
    does not appear to refer to a file or URI, a ``None`` is
    returned.

    :type path: str
    :param path: The resource URI, e.g. file://foo.txt.  This value
        may also be a non resource URI, in which case ``None`` is returned.

    :return: The loaded value associated with the resource URI.
        If the provided ``path`` is not a resource URI, then a
        value of ``None`` is returned.

    """
    data = None
    if isinstance(path, six.string_types):
        for prefix, function_spec in PREFIX_MAP.items():
            if path.startswith(prefix):
                function, kwargs = function_spec
                data = function(prefix, path, **kwargs)
    return data


def get_file(prefix, path, mode):
    file_path = os.path.expandvars(os.path.expanduser(path[len(prefix):]))
    try:
        with compat_open(file_path, mode) as f:
            return f.read()
    except UnicodeDecodeError:
        raise ResourceLoadingError(
            'Unable to load paramfile (%s), text contents could '
            'not be decoded.  If this is a binary file, please use the '
            'fileb:// prefix instead of the file:// prefix.' % file_path)
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


PREFIX_MAP = {
    'file://': (get_file, {'mode': 'r'}),
    'fileb://': (get_file, {'mode': 'rb'}),
    'http://': (get_uri, {}),
    'https://': (get_uri, {}),
}

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
import copy
import logging
import os

from botocore.awsrequest import AWSRequest
from botocore.exceptions import ProfileNotFound
from botocore.httpsession import URLLib3Session

from awscli import argprocess
from awscli.compat import compat_open

logger = logging.getLogger(__name__)

# These are special cased arguments that do _not_ get the
# special param file processing.  This is typically because it
# refers to an actual URI of some sort and we don't want to actually
# download the content (i.e TemplateURL in cloudformation).
PARAMFILE_DISABLED = set(
    [
        'api-gateway.put-integration.uri',
        'api-gateway.create-integration.integration-uri',
        'api-gateway.update-integration.integration-uri',
        'api-gateway.create-api.target',
        'api-gateway.update-api.target',
        'appstream.create-stack.redirect-url',
        'appstream.create-stack.feedback-url',
        'appstream.update-stack.redirect-url',
        'appstream.update-stack.feedback-url',
        'cloudformation.create-stack.template-url',
        'cloudformation.update-stack.template-url',
        'cloudformation.create-stack-set.template-url',
        'cloudformation.update-stack-set.template-url',
        'cloudformation.create-change-set.template-url',
        'cloudformation.validate-template.template-url',
        'cloudformation.estimate-template-cost.template-url',
        'cloudformation.get-template-summary.template-url',
        'cloudformation.create-stack.stack-policy-url',
        'cloudformation.update-stack.stack-policy-url',
        'cloudformation.set-stack-policy.stack-policy-url',
        # aws cloudformation package --template-file
        'custom.package.template-file',
        # aws cloudformation deploy --template-file
        'custom.deploy.template-file',
        'cloudformation.update-stack.stack-policy-during-update-url',
        'cloudformation.register-type.schema-handler-package',
        # We will want to change the event name to ``s3`` as opposed to
        # custom in the near future along with ``s3`` to ``s3api``.
        'custom.cp.website-redirect',
        'custom.mv.website-redirect',
        'custom.sync.website-redirect',
        'guardduty.create-ip-set.location',
        'guardduty.update-ip-set.location',
        'guardduty.create-threat-intel-set.location',
        'guardduty.update-threat-intel-set.location',
        'comprehend.detect-dominant-language.text',
        'comprehend.batch-detect-dominant-language.text-list',
        'comprehend.detect-entities.text',
        'comprehend.batch-detect-entities.text-list',
        'comprehend.detect-key-phrases.text',
        'comprehend.batch-detect-key-phrases.text-list',
        'comprehend.detect-sentiment.text',
        'comprehend.batch-detect-sentiment.text-list',
        'emr.create-studio.idp-auth-url',
        'iam.create-open-id-connect-provider.url',
        'machine-learning.predict.predict-endpoint',
        'mediatailor.put-playback-configuration.ad-decision-server-url',
        'mediatailor.put-playback-configuration.slate-ad-url',
        'mediatailor.put-playback-configuration.video-content-source-url',
        'rds.copy-db-cluster-snapshot.pre-signed-url',
        'rds.create-db-cluster.pre-signed-url',
        'rds.copy-db-snapshot.pre-signed-url',
        'rds.create-db-instance-read-replica.pre-signed-url',
        'sagemaker.create-notebook-instance.default-code-repository',
        'sagemaker.create-notebook-instance.additional-code-repositories',
        'sagemaker.update-notebook-instance.default-code-repository',
        'sagemaker.update-notebook-instance.additional-code-repositories',
        'serverlessapplicationrepository.create-application.home-page-url',
        'serverlessapplicationrepository.create-application.license-url',
        'serverlessapplicationrepository.create-application.readme-url',
        'serverlessapplicationrepository.create-application.source-code-url',
        'serverlessapplicationrepository.create-application.template-url',
        'serverlessapplicationrepository.create-application-version.source-code-url',
        'serverlessapplicationrepository.create-application-version.template-url',
        'serverlessapplicationrepository.update-application.home-page-url',
        'serverlessapplicationrepository.update-application.readme-url',
        'service-catalog.create-product.support-url',
        'service-catalog.update-product.support-url',
        'ses.create-custom-verification-email-template.failure-redirection-url',
        'ses.create-custom-verification-email-template.success-redirection-url',
        'ses.put-account-details.website-url',
        'ses.update-custom-verification-email-template.failure-redirection-url',
        'ses.update-custom-verification-email-template.success-redirection-url',
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
        'sqs.list-queue-tags.queue-url',
        'sqs.tag-queue.queue-url',
        'sqs.untag-queue.queue-url',
        's3.copy-object.website-redirect-location',
        's3.create-multipart-upload.website-redirect-location',
        's3.put-object.website-redirect-location',
        # Double check that this has been renamed!
        'sns.subscribe.notification-endpoint',
        'iot.create-job.document-source',
        'translate.translate-text.text',
        'workdocs.create-notification-subscription.notification-endpoint',
    ]
)


class ResourceLoadingError(Exception):
    pass


def register_uri_param_handler(session, **kwargs):
    prefix_map = copy.deepcopy(LOCAL_PREFIX_MAP)
    try:
        fetch_url = (
            session.get_scoped_config().get('cli_follow_urlparam', 'true')
            == 'true'
        )
    except ProfileNotFound:
        # If a --profile is provided that does not exist, loading
        # a value from get_scoped_config will crash the CLI.
        # This function can be called as the first handler for
        # the session-initialized event, which happens before a
        # profile can be created, even if the command would have
        # successfully created a profile. Instead of crashing here
        # on a ProfileNotFound the CLI should just use 'none'.
        fetch_url = True

    if fetch_url:
        prefix_map.update(REMOTE_PREFIX_MAP)

    handler = URIArgumentHandler(prefix_map)
    session.register('load-cli-arg', handler)


class URIArgumentHandler:
    def __init__(self, prefixes=None):
        if prefixes is None:
            prefixes = copy.deepcopy(LOCAL_PREFIX_MAP)
            prefixes.update(REMOTE_PREFIX_MAP)
        self._prefixes = prefixes

    def __call__(self, event_name, param, value, **kwargs):
        """Handler that supports param values from URIs."""
        cli_argument = param
        qualified_param_name = '.'.join(event_name.split('.')[1:])
        if qualified_param_name in PARAMFILE_DISABLED or getattr(
            cli_argument, 'no_paramfile', None
        ):
            return
        else:
            return self._check_for_uri_param(cli_argument, value)

    def _check_for_uri_param(self, param, value):
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
        try:
            return get_paramfile(value, self._prefixes)
        except ResourceLoadingError as e:
            raise argprocess.ParamError(param.cli_name, str(e))


def get_paramfile(path, cases):
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

    :type cases: dict
    :param cases: A dictionary of URI prefixes to function mappings
        that a parameter is checked against.

    :return: The loaded value associated with the resource URI.
        If the provided ``path`` is not a resource URI, then a
        value of ``None`` is returned.

    """
    data = None
    if isinstance(path, str):
        for prefix, function_spec in cases.items():
            if path.startswith(prefix):
                function, kwargs = function_spec
                data = function(prefix, path, **kwargs)
    return data


def get_file(prefix, path, mode):
    file_path = os.path.expandvars(os.path.expanduser(path[len(prefix) :]))
    try:
        with compat_open(file_path, mode) as f:
            return f.read()
    except UnicodeDecodeError:
        raise ResourceLoadingError(
            'Unable to load paramfile (%s), text contents could '
            'not be decoded.  If this is a binary file, please use the '
            'fileb:// prefix instead of the file:// prefix.' % file_path
        )
    except OSError as e:
        raise ResourceLoadingError(
            f'Unable to load paramfile {path}: {e}'
        )


def get_uri(prefix, uri):
    try:
        session = URLLib3Session()
        r = session.send(AWSRequest('GET', uri).prepare())
        if r.status_code == 200:
            return r.text
        else:
            raise ResourceLoadingError(
                f"received non 200 status code of {r.status_code}"
            )
    except Exception as e:
        raise ResourceLoadingError('Unable to retrieve %s: %s' % (uri, e))


LOCAL_PREFIX_MAP = {
    'file://': (get_file, {'mode': 'r'}),
    'fileb://': (get_file, {'mode': 'rb'}),
}


REMOTE_PREFIX_MAP = {
    'http://': (get_uri, {}),
    'https://': (get_uri, {}),
}

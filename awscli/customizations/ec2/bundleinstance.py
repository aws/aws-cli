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

import logging
from hashlib import sha1
import hmac
import base64
import datetime

from awscli.arguments import CustomArgument

logger = logging.getLogger('ec2bundleinstance')

# This customization adds the following scalar parameters to the
# bundle-instance operation:

# --bucket:
BUCKET_DOCS = ('The bucket in which to store the AMI.  '
               'You can specify a bucket that you already own or '
               'a new bucket that Amazon EC2 creates on your behalf.  '
               'If you specify a bucket that belongs to someone else, '
               'Amazon EC2 returns an error.')

# --prefix:
PREFIX_DOCS = ('The prefix for the image component names being stored '
               'in Amazon S3.')

# --owner-akid
OWNER_AKID_DOCS = 'The access key ID of the owner of the Amazon S3 bucket.'

# --policy
POLICY_DOCS = (
    "An Amazon S3 upload policy that gives "
    "Amazon EC2 permission to upload items into Amazon S3 "
    "on the user's behalf. If you provide this parameter, "
    "you must also provide "
    "your secret access key, so we can create a policy "
    "signature for you (the secret access key is not passed "
    "to Amazon EC2). If you do not provide this parameter, "
    "we generate an upload policy for you automatically. "
    "For more information about upload policies see the "
    "sections about policy construction and signatures in the "
    '<a href="http://docs.aws.amazon.com/AmazonS3/latest/dev'
    '/HTTPPOSTForms.html">'
    'Amazon Simple Storage Service Developer Guide</a>.')

# --owner-sak
OWNER_SAK_DOCS = ('The AWS secret access key for the owner of the '
                  'Amazon S3 bucket specified in the --bucket '
                  'parameter. This parameter is required so that a '
                  'signature can be computed for the policy.')


def _add_params(argument_table, **kwargs):
    # Add the scalar parameters and also change the complex storage
    # param to not be required so the user doesn't get an error from
    # argparse if they only supply scalar params.
    storage_arg = argument_table['storage']
    storage_arg.required = False
    arg = BundleArgument(storage_param='Bucket',
                         name='bucket',
                         help_text=BUCKET_DOCS)
    argument_table['bucket'] = arg
    arg = BundleArgument(storage_param='Prefix',
                         name='prefix',
                         help_text=PREFIX_DOCS)
    argument_table['prefix'] = arg
    arg = BundleArgument(storage_param='AWSAccessKeyId',
                         name='owner-akid',
                         help_text=OWNER_AKID_DOCS)
    argument_table['owner-akid'] = arg
    arg = BundleArgument(storage_param='_SAK',
                         name='owner-sak',
                         help_text=OWNER_SAK_DOCS)
    argument_table['owner-sak'] = arg
    arg = BundleArgument(storage_param='UploadPolicy',
                         name='policy',
                         help_text=POLICY_DOCS)
    argument_table['policy'] = arg


def _check_args(parsed_args, **kwargs):
    # This function checks the parsed args.  If the user specified
    # the --ip-permissions option with any of the scalar options we
    # raise an error.
    logger.debug(parsed_args)
    arg_dict = vars(parsed_args)
    if arg_dict['storage']:
        for key in ('bucket', 'prefix', 'owner_akid',
                    'owner_sak', 'policy'):
            if arg_dict[key]:
                msg = ('Mixing the --storage option '
                       'with the simple, scalar options is '
                       'not recommended.')
                raise ValueError(msg)

POLICY = ('{{"expiration": "{expires}",'
          '"conditions": ['
          '{{"bucket": "{bucket}"}},'
          '{{"acl": "ec2-bundle-read"}},'
          '["starts-with", "$key", "{prefix}"]'
          ']}}'
          )


def _generate_policy(params):
    # Called if there is no policy supplied by the user.
    # Creates a policy that provides access for 24 hours.
    delta = datetime.timedelta(hours=24)
    expires = datetime.datetime.utcnow() + delta
    expires_iso = expires.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    policy = POLICY.format(expires=expires_iso,
                           bucket=params['Bucket'],
                           prefix=params['Prefix'])
    params['UploadPolicy'] = policy


def _generate_signature(params):
    # If we have a policy and a sak, create the signature.
    policy = params.get('UploadPolicy')
    sak = params.get('_SAK')
    if policy and sak:
        policy = base64.b64encode(policy.encode('latin-1')).decode('utf-8')
        new_hmac = hmac.new(sak.encode('utf-8'), digestmod=sha1)
        new_hmac.update(policy.encode('latin-1'))
        ps = base64.encodebytes(new_hmac.digest()).strip().decode('utf-8')
        params['UploadPolicySignature'] = ps
        del params['_SAK']


def _check_params(params, **kwargs):
    # Called just before call but prior to building the params.
    # Adds information not supplied by the user.
    storage = params['Storage']['S3']
    if 'UploadPolicy' not in storage:
        _generate_policy(storage)
    if 'UploadPolicySignature' not in storage:
        _generate_signature(storage)


EVENTS = [
    ('building-argument-table.ec2.bundle-instance', _add_params),
    ('operation-args-parsed.ec2.bundle-instance', _check_args),
    ('before-parameter-build.ec2.BundleInstance', _check_params),
]


def register_bundleinstance(event_handler):
    # Register all of the events for customizing BundleInstance
    for event, handler in EVENTS:
        event_handler.register(event, handler)


class BundleArgument(CustomArgument):

    def __init__(self, storage_param, *args, **kwargs):
        super(BundleArgument, self).__init__(*args, **kwargs)
        self._storage_param = storage_param

    def _build_storage(self, params, value):
        # Build up the Storage data structure
        if 'Storage' not in params:
            params['Storage'] = {'S3': {}}
        params['Storage']['S3'][self._storage_param] = value

    def add_to_params(self, parameters, value):
        if value:
            self._build_storage(parameters, value)

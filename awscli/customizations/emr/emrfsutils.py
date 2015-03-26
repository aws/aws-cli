# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.customizations.emr import constants
from awscli.customizations.emr import emrutils
from awscli.customizations.emr import exceptions


CONSISTENT_OPTIONAL_KEYS = ['RetryCount', 'RetryPeriod']
CSE_KMS_REQUIRED_KEYS = ['KMSKeyId']
CSE_CUSTOM_REQUIRED_KEYS = ['CustomProviderLocation', 'CustomProviderClass']
CSE_PROVIDER_TYPES = [constants.EMRFS_KMS, constants.EMRFS_CUSTOM]
ENCRYPTION_TYPES = [constants.EMRFS_CLIENT_SIDE, constants.EMRFS_SERVER_SIDE]

CONSISTENT_OPTION_NAME = "--emrfs Consistent=true/false"
CSE_OPTION_NAME = '--emrfs Encryption=ClientSide'
CSE_KMS_OPTION_NAME = '--emrfs Encryption=ClientSide,ProviderType=KMS'
CSE_CUSTOM_OPTION_NAME = '--emrfs Encryption=ClientSide,ProviderType=Custom'


def build_bootstrap_action_configs(region, emrfs_args):
    bootstrap_actions = []

    _verify_emrfs_args(emrfs_args)

    if _need_to_configure_cse(emrfs_args, 'CUSTOM'):
        # Download custom encryption provider from Amazon S3 to EMR Cluster
        bootstrap_actions.append(
            emrutils.build_bootstrap_action(
                path=constants.EMRFS_CSE_CUSTOM_S3_GET_BA_PATH,
                name=constants.S3_GET_BA_NAME,
                args=[constants.S3_GET_BA_SRC,
                      emrfs_args.get('CustomProviderLocation'),
                      constants.S3_GET_BA_DEST,
                      constants.EMRFS_CUSTOM_DEST_PATH,
                      constants.S3_GET_BA_FORCE]))

    emrfs_setup_ba_args = _build_ba_args_to_setup_emrfs(emrfs_args)
    bootstrap_actions.append(
        emrutils.build_bootstrap_action(
            path=emrutils.build_s3_link(
                relative_path=constants.CONFIG_HADOOP_PATH,
                region=region),
            name=constants.EMRFS_BA_NAME,
            args=emrfs_setup_ba_args))

    return bootstrap_actions


def _verify_emrfs_args(emrfs_args):
    # Encryption should have a valid value
    if 'Encryption' in emrfs_args \
            and emrfs_args['Encryption'].upper() not in ENCRYPTION_TYPES:
        raise exceptions.UnknownEncryptionTypeError(
            encryption=emrfs_args['Encryption'])

    # Only one of SSE and Encryption should be configured
    if 'SSE' in emrfs_args and 'Encryption' in emrfs_args:
        raise exceptions.BothSseAndEncryptionConfiguredError(
            sse=emrfs_args['SSE'], encryption=emrfs_args['Encryption'])

    # CSE should be configured correctly
    # ProviderType should be present and should have valid value
    # Given the type, the required parameters should be present
    if 'Encryption' in emrfs_args \
            and emrfs_args['Encryption'].upper() == constants.EMRFS_CLIENT_SIDE:
        if 'ProviderType' not in emrfs_args:
            raise exceptions.MissingParametersError(
                object_name=CSE_OPTION_NAME, missing='ProviderType')
        elif emrfs_args['ProviderType'].upper() not in CSE_PROVIDER_TYPES:
            raise exceptions.UnknownCseProviderTypeError(
                provider_type=emrfs_args['ProviderType'])
        elif emrfs_args['ProviderType'].upper() == 'KMS':
            _verify_required_args(emrfs_args.keys(), CSE_KMS_REQUIRED_KEYS,
                                  CSE_KMS_OPTION_NAME)
        elif emrfs_args['ProviderType'].upper() == 'CUSTOM':
            _verify_required_args(emrfs_args.keys(), CSE_CUSTOM_REQUIRED_KEYS,
                                  CSE_CUSTOM_OPTION_NAME)

    # No child attributes should be present if the parent feature is not
    # configured
    if 'Consistent' not in emrfs_args:
        _verify_child_args(emrfs_args.keys(), CONSISTENT_OPTIONAL_KEYS,
                           CONSISTENT_OPTION_NAME)
    if not _need_to_configure_cse(emrfs_args, 'KMS'):
        _verify_child_args(emrfs_args.keys(), CSE_KMS_REQUIRED_KEYS,
                           CSE_KMS_OPTION_NAME)
    if not _need_to_configure_cse(emrfs_args, 'CUSTOM'):
        _verify_child_args(emrfs_args.keys(), CSE_CUSTOM_REQUIRED_KEYS,
                           CSE_CUSTOM_OPTION_NAME)


def _verify_required_args(actual_keys, required_keys, object_name):
    if any(x not in actual_keys for x in required_keys):
        missing_keys = list(
            sorted(set(required_keys).difference(set(actual_keys))))
        raise exceptions.MissingParametersError(
            object_name=object_name, missing=emrutils.join(missing_keys))


def _verify_child_args(actual_keys, child_keys, parent_object_name):
    if any(x in actual_keys for x in child_keys):
        invalid_keys = list(
            sorted(set(child_keys).intersection(set(actual_keys))))
        raise exceptions.InvalidEmrFsArgumentsError(
            invalid=emrutils.join(invalid_keys),
            parent_object_name=parent_object_name)


def _build_ba_args_to_setup_emrfs(emrfs_args):
    """
    Assumption: emrfs_args is valid i.e. all required attributes are present
    """
    ba_args = []

    if _need_to_configure_consistent_view(emrfs_args):
        _update_ba_args_for_consistent_view(ba_args, emrfs_args)

    if _need_to_configure_sse(emrfs_args):
        _update_ba_args_for_sse(ba_args, emrfs_args)

    if _need_to_configure_cse(emrfs_args, 'KMS'):
        _update_ba_args_for_cse(ba_args, emrfs_args, 'KMS')

    if _need_to_configure_cse(emrfs_args, 'CUSTOM'):
        _update_ba_args_for_cse(ba_args, emrfs_args, 'CUSTOM')

    if 'Args' in emrfs_args:
        for arg_value in emrfs_args.get('Args'):
            _update_ba_args_main(ba_args, arg_value)

    return ba_args


def _need_to_configure_consistent_view(emrfs_args):
    return 'Consistent' in emrfs_args


def _need_to_configure_sse(emrfs_args):
    return 'SSE' in emrfs_args \
        or ('Encryption' in emrfs_args
            and emrfs_args['Encryption'].upper() == constants.EMRFS_SERVER_SIDE)


def _need_to_configure_cse(emrfs_args, cse_type):
    return ('Encryption' in emrfs_args
            and emrfs_args['Encryption'].upper() == constants.EMRFS_CLIENT_SIDE
            and 'ProviderType' in emrfs_args
            and emrfs_args['ProviderType'].upper() == cse_type)


def _update_ba_args_for_consistent_view(ba_args, emrfs_args):
    _update_ba_args(ba_args,
                    constants.EMRFS_CONSISTENT_KEY,
                    str(emrfs_args['Consistent']).lower())

    if 'RetryCount' in emrfs_args:
        _update_ba_args(ba_args, constants.EMRFS_RETRY_COUNT_KEY,
                        str(emrfs_args['RetryCount']))

    if 'RetryPeriod' in emrfs_args:
        _update_ba_args(ba_args, constants.EMRFS_RETRY_PERIOD_KEY,
                        str(emrfs_args['RetryPeriod']))


def _update_ba_args_for_sse(ba_args, emrfs_args):
    sse_value = emrfs_args['SSE'] if 'SSE' in emrfs_args else True
    # if 'SSE' is not in emrfs_args then 'Encryption' must be 'ServerSide'

    _update_ba_args(
        ba_args, constants.EMRFS_SSE_KEY, str(sse_value).lower())


def _update_ba_args_for_cse(ba_args, emrfs_args, cse_type):
    _update_ba_args(ba_args, constants.EMRFS_CSE_KEY, 'true')
    if cse_type == 'KMS':
        _update_ba_args(ba_args,
                        constants.EMRFS_CSE_ENCRYPTION_MATERIALS_PROVIDER_KEY,
                        constants.EMRFS_CSE_KMS_PROVIDER_FULL_CLASS_NAME)
        _update_ba_args(
            ba_args, constants.EMRFS_CSE_KMS_KEY_ID_KEY, emrfs_args['KMSKeyId'])
    elif cse_type == 'CUSTOM':
        _update_ba_args(ba_args,
                        constants.EMRFS_CSE_ENCRYPTION_MATERIALS_PROVIDER_KEY,
                        emrfs_args['CustomProviderClass'])


def _update_ba_args_main(ba_args, key_value):
    ba_args.append(constants.EMRFS_BA_ARG_KEY)
    ba_args.append(key_value)


def _update_ba_args(ba_args, key, value):
    _update_ba_args_main(ba_args, "%s=%s" % (key, value))

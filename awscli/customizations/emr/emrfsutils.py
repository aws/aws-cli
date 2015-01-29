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

from awscli.customizations.emr import constants
from awscli.customizations.emr import emrutils
from awscli.customizations.emr import exceptions


def build_emrfs_args(parsed_globals, parsed_emrfs):
    """
    Parse parameters of create-cluster --emrfs option
    and build bootstrap_actions to configurate EMRFS
    """
    bootstrap_actions = []
    args = []
    common_keys = ['RetryCount', 'RetryPeriod', 'Consistent', 'Args']
    cse_common_keys = common_keys + ['Encryption', 'ProviderType']

    if parsed_emrfs.get('SSE') is None and \
            parsed_emrfs.get('Encryption') is None:
        _validate_expected_keys(
            expected_keys=common_keys,
            actual_keys=parsed_emrfs.keys(),
            whitelisted_keys=[],
            exception=exceptions.InvalidEMRFSArgumentsError(
                valid_options=''))
    elif parsed_emrfs.get('SSE') is not None:
        validate = _validate_expected_keys(
            expected_keys=['SSE'],
            actual_keys=parsed_emrfs.keys(),
            whitelisted_keys=common_keys,
            exception=exceptions.InvalidEMRFSArgumentsError(
                valid_options=''))
        args.append(constants.EMRFS_BA_ARG_KEY)
        args.append(
            constants.EMRFS_SSE_KEY + '=' +
            str(parsed_emrfs.get('SSE')).lower())
    elif parsed_emrfs.get('Encryption') is not None:
        encryption_type = parsed_emrfs.get('Encryption').upper()

        if encryption_type == constants.EMRFS_SERVER_SIDE:
            _validate_expected_keys(
                expected_keys=['Encryption'],
                actual_keys=parsed_emrfs.keys(),
                whitelisted_keys=common_keys,
                exception=exceptions.InvalidEMRFSArgumentsError(
                    valid_options=(
                        'You can specify the following parameters when'
                        ' using server-side encryption: RetryCount, '
                        'RetryPeriod, Consistent, and Args.')))
            args.append(constants.EMRFS_BA_ARG_KEY)
            args.append(constants.EMRFS_SSE_KEY + '=true')
        elif encryption_type == constants.EMRFS_CLIENT_SIDE:
            args.append(constants.EMRFS_BA_ARG_KEY)
            args.append(constants.EMRFS_CSE_ENABLED + '=true')

            provider_type = parsed_emrfs.get('ProviderType')
            if provider_type is None:
                raise exceptions.MissingParametersError(
                    object_name='--emrfs Encryption=ClientSide',
                    missing='ProviderType')

            elif provider_type.upper() == 'KMS':
                _validate_required_keys(
                    required_keys=['KeyId'],
                    actual_keys=parsed_emrfs.keys(),
                    structure='--emrfs Encryption=ClientSide,ProviderType=KMS')
                _validate_expected_keys(
                    expected_keys=['KeyId'],
                    actual_keys=parsed_emrfs.keys(),
                    whitelisted_keys=cse_common_keys,
                    exception=exceptions.InvalidEMRFSArgumentsError(
                        valid_options=(
                            'You must specify an AWS KMS KeyId when '
                            'using EMRFS client-side encryption with '
                            'ProviderType=KMS.')))
                args.append(constants.EMRFS_BA_ARG_KEY)
                args.append(
                    constants.EMRFS_CSE_ENCRYPTION_MATERIALS_PROVIDER_KEY +
                    '=' + constants.EMRFS_CSE_KMS_PROVIDER_FULL_CLASS_NAME)
                args.append(constants.EMRFS_BA_ARG_KEY)
                args.append(constants.EMRFS_CSE_KMS_KEY_ID + '=' +
                            str(parsed_emrfs.get('KeyId')))

            elif provider_type.upper() == 'RSA':
                _validate_required_keys(
                    required_keys=['PrivateKey', 'PublicKey',
                                   'RSAKeyPairName'],
                    actual_keys=parsed_emrfs.keys(),
                    structure='--emrfs Encryption=ClientSide,ProviderType=RSA')
                _validate_expected_keys(
                    expected_keys=['PrivateKey', 'PublicKey',
                                   'RSAKeyPairName'],
                    actual_keys=parsed_emrfs.keys(),
                    whitelisted_keys=cse_common_keys,
                    exception=exceptions.InvalidEMRFSArgumentsError(
                        valid_options=(
                            'You must specify a PrivateKey, PublicKey and '
                            'RSAKeyPairName when using EMRFS client-side '
                            'encryption with ProviderType=RSA.')))
                args.append(constants.EMRFS_BA_ARG_KEY)
                args.append(
                    constants.EMRFS_CSE_ENCRYPTION_MATERIALS_PROVIDER_KEY +
                    '=' + constants.EMRFS_CSE_RSA_PROVIDER_FULL_CLASS_NAME)
                args.append(constants.EMRFS_BA_ARG_KEY)
                args.append(constants.EMRFS_CSE_RSA_PRIVATE_KEY + '=' +
                            str(parsed_emrfs.get('PrivateKey')))
                args.append(constants.EMRFS_BA_ARG_KEY)
                args.append(constants.EMRFS_CSE_RSA_PUBLIC_KEY + '=' +
                            str(parsed_emrfs.get('PublicKey')))
                args.append(constants.EMRFS_BA_ARG_KEY)
                args.append(constants.EMRFS_CSE_RSA_KEY_PAIR_NAME + '=' +
                            str(parsed_emrfs.get('RSAKeyPairName')))

            elif provider_type.upper() == 'CUSTOM':
                _validate_required_keys(
                    required_keys=['ProviderLocation', 'ProviderClassName'],
                    actual_keys=parsed_emrfs.keys(),
                    structure=('--emrfs Encryption=ClientSide,'
                               'ProviderType=CUSTOM'))
                _validate_expected_keys(
                    expected_keys=['ProviderLocation', 'ProviderClassName'],
                    actual_keys=parsed_emrfs.keys(),
                    whitelisted_keys=cse_common_keys,
                    exception=exceptions.InvalidEMRFSArgumentsError(
                        valid_options=(
                            'You must specify a ProviderLocation and '
                            'ProviderClassName when using EMRFS client-side '
                            'encryption with ProviderType=CUSTOM')))
                # Download custom encryption provider
                # from Amazon S3 to EMR Cluster
                bootstrap_actions.append(
                    emrutils.build_bootstrap_action(
                        path=constants.EMRFS_CSE_CUSTOM_S3_GET_BA_PATH,
                        name=constants.S3_GET_BA_NAME,
                        args=[constants.S3_GET_BA_SRC,
                              parsed_emrfs.get('ProviderLocation'),
                              constants.S3_GET_BA_DEST,
                              constants.EMRFS_CUSTOM_DEST_PATH,
                              constants.S3_GET_BA_FORCE]))

                args.append(constants.EMRFS_BA_ARG_KEY)
                args.append(
                    constants.EMRFS_CSE_ENCRYPTION_MATERIALS_PROVIDER_KEY +
                    '=' + str(parsed_emrfs.get('ProviderClassName')))

            else:
                raise exceptions.UnknownCSEProviderTypeError(
                    provider_type=provider_type)
        else:
            raise exceptions.InvalidEMRFSArgumentsError(
                valid_options=('Encryption type must be either '
                               '"ServerSide" or "ClientSide".'))

    # Common configuration options
    if parsed_emrfs.get('Consistent') is not None:
        args.append(constants.EMRFS_BA_ARG_KEY)
        args.append(
            constants.EMRFS_CONSISTENT_KEY +
            '=' + str(parsed_emrfs.get('Consistent')).lower())

    if parsed_emrfs.get('RetryCount') is not None:
        args.append(constants.EMRFS_BA_ARG_KEY)
        args.append(
            constants.EMRFS_RETRY_COUNT_KEY + '=' +
            str(parsed_emrfs.get('RetryCount')))

    if parsed_emrfs.get('RetryPeriod') is not None:
        args.append(constants.EMRFS_BA_ARG_KEY)
        args.append(
            constants.EMRFS_RETRY_PERIOD_KEY + '=' +
            str(parsed_emrfs.get('RetryPeriod')))

    if parsed_emrfs.get('Args') is not None:
        for arg in parsed_emrfs.get('Args'):
            args.append(constants.EMRFS_BA_ARG_KEY)
            args.append(arg)

    bootstrap_actions.append(
        emrutils.build_bootstrap_action(
            path=emrutils.build_s3_link(
                relative_path=constants.CONFIG_HADOOP_PATH,
                region=parsed_globals.region),
            name=constants.EMRFS_BA_NAME,
            args=args))

    return bootstrap_actions


def _validate_expected_keys(
        expected_keys, actual_keys,
        whitelisted_keys, exception):
    """
    Utility method to validate if actual_keys is a subset of
    the union of expected_keys and whitelisted_keys
    """
    if not set(actual_keys).issubset(
            set(expected_keys + whitelisted_keys)):
        raise exception
    else:
        return True


def _validate_required_keys(required_keys, actual_keys, structure='--emrfs'):
    for required_key in required_keys:
        if required_key not in actual_keys:
            raise exceptions.MissingParametersError(
                object_name=structure,
                missing=required_key)

    return True

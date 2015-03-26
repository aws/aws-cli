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
import os

from awscli.customizations.emr.emrfsutils import build_bootstrap_action_configs
from awscli.customizations.emr.emrfsutils import CONSISTENT_OPTION_NAME
from awscli.customizations.emr.emrfsutils import CSE_CUSTOM_OPTION_NAME
from awscli.customizations.emr.emrfsutils import CSE_KMS_OPTION_NAME
from awscli.customizations.emr.emrfsutils import CSE_OPTION_NAME


from tests.unit.customizations.emr import EMRBaseAWSCommandParamsTest as \
    BaseAWSCommandParamsTest
import argparse


DEFAULT_INSTANCES = {
    'KeepJobFlowAliveWhenNoSteps': True,
    'TerminationProtected': False,
    'InstanceGroups': [{
        'InstanceRole': 'MASTER',
        'InstanceCount': 1,
        'Name': 'MASTER',
        'Market': 'ON_DEMAND',
        'InstanceType': 'm1.large'
    }]
}

DEFAULT_CMD = ('emr create-cluster --ami-version 3.4 --use-default-roles'
               ' --instance-type m1.large ')
DEFAULT_RESULT = {
    'Name': "Development Cluster",
    'Instances': DEFAULT_INSTANCES,
    'AmiVersion': '3.4',
    'VisibleToAllUsers': True,
    'JobFlowRole': "EMR_EC2_DefaultRole",
    'ServiceRole': "EMR_DefaultRole",
    'Tags': []
}


class TestEmrfsUtils(BaseAWSCommandParamsTest):

    def test_consistent(self):
        emrfs_option_value = 'Consistent=true'
        setup_emrfs_ba_key_values = [
            'fs.s3.consistent=true'
        ]
        self._assert_bootstrap_actions(
            emrfs_option_value, setup_emrfs_ba_key_values)

    def test_consistent_w_optional_args(self):
        emrfs_option_value = 'Consistent=true,RetryCount=5,RetryPeriod=30'
        setup_emrfs_ba_key_values = [
            'fs.s3.consistent=true', 'fs.s3.consistent.retryCount=5',
            'fs.s3.consistent.retryPeriodSeconds=30'
        ]
        self._assert_bootstrap_actions(
            emrfs_option_value, setup_emrfs_ba_key_values)

    def test_consistent_false_w_optional_args(self):
        emrfs_option_value = 'Consistent=false,RetryCount=5'
        setup_emrfs_ba_key_values = [
            'fs.s3.consistent=false', 'fs.s3.consistent.retryCount=5'
        ]
        self._assert_bootstrap_actions(
            emrfs_option_value, setup_emrfs_ba_key_values)

    def test_sse(self):
        emrfs_option_value = 'SSE=true'
        setup_emrfs_ba_key_values = [
            'fs.s3.enableServerSideEncryption=true'
        ]
        self._assert_bootstrap_actions(
            emrfs_option_value, setup_emrfs_ba_key_values)

        emrfs_option_value = 'Encryption=ServerSide'
        setup_emrfs_ba_key_values = [
            'fs.s3.enableServerSideEncryption=true'
        ]
        self._assert_bootstrap_actions(
            emrfs_option_value, setup_emrfs_ba_key_values)

    def test_cse_kms(self):
        emrfs_option_value = 'Encryption=ClientSide,ProviderType=KMS,' \
            'KMSKeyId=my_key'
        setup_emrfs_ba_key_values = [
            'fs.s3.cse.enabled=true', 'fs.s3.cse.encryptionMaterialsProvider='
            'com.amazon.ws.emr.hadoop.fs.cse.KMSEncryptionMaterialsProvider',
            'fs.s3.cse.kms.keyId=my_key'
        ]
        self._assert_bootstrap_actions(
            emrfs_option_value, setup_emrfs_ba_key_values)

    def test_cse_custom(self):
        emrfs_option_value = 'Encryption=ClientSide,ProviderType=Custom,' \
            'CustomProviderLocation=my_location,CustomProviderClass=my_class'
        setup_emrfs_ba_key_values = [
            'fs.s3.cse.enabled=true', 'fs.s3.cse.encryptionMaterialsProvider='
            'my_class'
        ]
        self._assert_bootstrap_actions(
            emrfs_option_value, setup_emrfs_ba_key_values, 'my_location')

    def test_sse_and_consistent(self):
        self._assert_bootstrap_actions(
            emrfs_option_value='SSE=true,Consistent=true',
            setup_emrfs_ba_key_values=[
                'fs.s3.consistent=true', 'fs.s3.enableServerSideEncryption=true'
            ])

        self._assert_bootstrap_actions(
            emrfs_option_value='Consistent=false,Encryption=serVERSIde',
            setup_emrfs_ba_key_values=[
                'fs.s3.consistent=false', 'fs.s3.enableServerSideEncryption=true'
            ])

    def test_cse_and_consistent(self):
        self._assert_bootstrap_actions(
            emrfs_option_value='Encryption=ClientSide,ProviderType=KMS,'
            'KMSKeyId=my_key,Consistent=true',
            setup_emrfs_ba_key_values=[
                'fs.s3.consistent=true', 'fs.s3.cse.enabled=true',
                'fs.s3.cse.encryptionMaterialsProvider=com.amazon.ws.emr.'
                'hadoop.fs.cse.KMSEncryptionMaterialsProvider',
                'fs.s3.cse.kms.keyId=my_key'
            ])

    def test_args_and_sse(self):
        self._assert_bootstrap_actions(
            emrfs_option_value='SSE=true,'
            'Args=[fs.s3.serverSideEncryptionAlgorithm=AES256]',
            setup_emrfs_ba_key_values=[
                'fs.s3.enableServerSideEncryption=true',
                'fs.s3.serverSideEncryptionAlgorithm=AES256'
            ])

    def test_args_and_cse(self):
        self._assert_bootstrap_actions(
            emrfs_option_value='Encryption=ClientSide,ProviderType=KMS,'
            'KMSKeyId=my_key,Args=[k1=v1]',
            setup_emrfs_ba_key_values=[
                'fs.s3.cse.enabled=true',
                'fs.s3.cse.encryptionMaterialsProvider=com.amazon.ws.emr.'
                'hadoop.fs.cse.KMSEncryptionMaterialsProvider',
                'fs.s3.cse.kms.keyId=my_key', 'k1=v1'
            ])

    def test_args_and_consistent(self):
        self._assert_bootstrap_actions(
            emrfs_option_value='Consistent=true,Args=[k1=v1,k2=v2]',
            setup_emrfs_ba_key_values=[
                'fs.s3.consistent=true', 'k1=v1', 'k2=v2'
            ])

    def test_only_args(self):
        self._assert_bootstrap_actions(
            emrfs_option_value='Args=[k1=v1,k2=v2]',
            setup_emrfs_ba_key_values=['k1=v1', 'k2=v2'])

    def test_using_json_file(self):
        data_path = os.path.join(
            os.path.dirname(__file__), 'input_emr_fs.json')
        self._assert_bootstrap_actions(
            emrfs_option_value='file://%s' % data_path,
            setup_emrfs_ba_key_values=[
                'fs.s3.consistent=true',
                'fs.s3.consistent.retryCount=10',
                'fs.s3.consistent.retryPeriodSeconds=3',
                'fs.s3.enableServerSideEncryption=false',
                'fs.s3.serverSideEncryptionAlgorithm=AES256',
                'fs.s3.sleepTimeSeconds=30'
            ])

    def test_only_one_encryption_type(self):
        self._assert_error_msg(
            emrfs_option_value='SSE=true,Encryption=ClientSide,'
            'ProviderType=KMS,KMSKeyId=k1',
            exception_class_name='BothSseAndEncryptionConfiguredError',
            error_msg_kwargs={'sse': 'True', 'encryption': 'ClientSide'}
        )

    def test_cse_missing_provider_type(self):
        self._assert_error_msg(
            emrfs_option_value='Encryption=ClientSide',
            exception_class_name='MissingParametersError',
            error_msg_kwargs={'object_name': CSE_OPTION_NAME,
                              'missing': 'ProviderType'}
        )

    def test_cse_kms_missing_key_id(self):
        self._assert_error_msg(
            emrfs_option_value='Encryption=ClientSide,ProviderType=KMS',
            exception_class_name='MissingParametersError',
            error_msg_kwargs={'object_name': CSE_KMS_OPTION_NAME,
                              'missing': 'KMSKeyId'}
        )

    def test_cse_custom_missing_all(self):
        self._assert_error_msg(
            emrfs_option_value='Encryption=ClientSide,ProviderType=Custom',
            exception_class_name='MissingParametersError',
            error_msg_kwargs={'object_name': CSE_CUSTOM_OPTION_NAME,
                              'missing': 'CustomProviderClass and '
                              'CustomProviderLocation'}
        )

    def test_cse_custom_missing_class(self):
        self._assert_error_msg(
            emrfs_option_value='Encryption=ClientSide,ProviderType=Custom,'
            'CustomProviderLocation=my_location',
            exception_class_name='MissingParametersError',
            error_msg_kwargs={'object_name': CSE_CUSTOM_OPTION_NAME,
                              'missing': 'CustomProviderClass'}
        )

    def test_valid_encryption(self):
        self._assert_error_msg(
            emrfs_option_value='Encryption=ClientSide1',
            exception_class_name='UnknownEncryptionTypeError',
            error_msg_kwargs={'encryption': 'ClientSide1'}
        )

    def test_valid_cse_provider_type(self):
        self._assert_error_msg(
            emrfs_option_value='Encryption=ClientSide,ProviderType=KMS1',
            exception_class_name='UnknownCseProviderTypeError',
            error_msg_kwargs={'provider_type': 'KMS1'}
        )

    def test_valid_consistent_args(self):
        self._assert_error_msg(
            emrfs_option_value='SSE=true,RetryCount=5,RetryPeriod=30',
            exception_class_name='InvalidEmrFsArgumentsError',
            error_msg_kwargs={'invalid': 'RetryCount and RetryPeriod',
                              'parent_object_name': CONSISTENT_OPTION_NAME}
        )

    def test_valid_cse_kms_args(self):
        self._assert_error_msg(
            emrfs_option_value='Consistent=true,KMSKeyId=k1',
            exception_class_name='InvalidEmrFsArgumentsError',
            error_msg_kwargs={'invalid': 'KMSKeyId',
                              'parent_object_name': CSE_KMS_OPTION_NAME}
        )

    def test_valid_cse_custom_args(self):
        self._assert_error_msg(
            emrfs_option_value='Consistent=true,CustomProviderLocation=loc',
            exception_class_name='InvalidEmrFsArgumentsError',
            error_msg_kwargs={'invalid': 'CustomProviderLocation',
                              'parent_object_name': CSE_CUSTOM_OPTION_NAME}
        )

    def _assert_error_msg(self, emrfs_option_value,
                          exception_class_name, error_msg_kwargs):
        self.assert_error_msg(
            cmd="%s --emrfs %s" % (DEFAULT_CMD, emrfs_option_value),
            exception_class_name=exception_class_name,
            error_msg_kwargs=error_msg_kwargs)

    def _assert_bootstrap_actions(self, emrfs_option_value,
                                  setup_emrfs_ba_key_values,
                                  provider_location=None):
        cmd = "%s --emrfs %s" % (DEFAULT_CMD, emrfs_option_value)
        result = copy.deepcopy(DEFAULT_RESULT)
        result['BootstrapActions'] = [self._create_s3_get_ba_config(
            provider_location)] if provider_location is not None else []
        result['BootstrapActions'] += [self._create_setup_emrfs_ba_config(
            setup_emrfs_ba_key_values)]

        self.assert_params_for_cmd(cmd, result)

    def _create_setup_emrfs_ba_config(self, ba_arg_values):
        ba_arg_keys = ['-e' for x in ba_arg_values]
        ba_args = [x for pair in zip(ba_arg_keys, ba_arg_values) for x in pair]

        return {
            'Name': 'Setup EMRFS',
            'ScriptBootstrapAction': {
                'Path': ('s3://us-east-1.elasticmapreduce/'
                         'bootstrap-actions/configure-hadoop'),
                'Args': ba_args
            }
        }

    def _create_s3_get_ba_config(self, provider_location):
        return {
            'Name': 'S3 get',
            'ScriptBootstrapAction': {
                'Path': 'file:/usr/share/aws/emr/scripts/s3get',
                'Args': [
                    '-s', provider_location,
                    '-d', '/usr/share/aws/emr/auxlib',
                    '-f'
                ]
            }
        }

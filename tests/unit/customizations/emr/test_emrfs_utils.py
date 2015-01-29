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

from tests.unit.customizations.emr import EMRBaseAWSCommandParamsTest as \
    BaseAWSCommandParamsTest
import copy
import os
import json
from mock import patch
from botocore.vendored import requests


DEFAULT_INSTANCES = {'KeepJobFlowAliveWhenNoSteps': True,
                     'TerminationProtected': False,
                     'InstanceGroups': [
                         {'InstanceRole': 'MASTER',
                          'InstanceCount': 1,
                          'Name': 'MASTER',
                          'Market': 'ON_DEMAND',
                          'InstanceType': 'm1.large'
                          }]
                     }

DEFAULT_CMD = ('emr create-cluster --ami-version 3.4 --use-default-roles'
               ' --instance-type m1.large ')
DEFAULT_RESULT = \
    {
        'Name': "Development Cluster",
        'Instances': DEFAULT_INSTANCES,
        'AmiVersion': '3.4',
        'VisibleToAllUsers': True,
        'JobFlowRole': "EMR_EC2_DefaultRole",
        'ServiceRole': "EMR_DefaultRole",
        'Tags': []
    }


class TestEmrfsUtils(BaseAWSCommandParamsTest):
    def test_emrfs_server_side_encryption(self):
        # Use SSE shortcut
        cmd = DEFAULT_CMD +\
            ('--emrfs Consistent=true,SSE=false,RetryCount=10,'
             'RetryPeriod=3,Args=[fs.s3.serverSideEncryptionAlgorithm='
             'AES256,fs.s3.sleepTimeSeconds=30]')
        emf_fs_ba_config = \
            {'Name': 'Setup EMRFS',
             'ScriptBootstrapAction':
                {'Path': ('s3://us-east-1.elasticmapreduce/'
                          'bootstrap-actions/configure-hadoop'),
                 'Args': ['-e',
                          'fs.s3.enableServerSideEncryption=false',
                          '-e',
                          'fs.s3.consistent=true',
                          '-e',
                          'fs.s3.consistent.retryCount=10',
                          '-e',
                          'fs.s3.consistent.retryPeriodSeconds=3',
                          '-e',
                          'fs.s3.serverSideEncryptionAlgorithm=AES256',
                          '-e',
                          'fs.s3.sleepTimeSeconds=30']
                 }
             }
        result = copy.deepcopy(DEFAULT_RESULT)
        result['BootstrapActions'] = [emf_fs_ba_config]
        self.assert_params_for_cmd2(cmd, result)

        data_path = os.path.join(
            os.path.dirname(__file__), 'input_emr_fs.json')
        cmd = DEFAULT_CMD + '--emrfs file://' + data_path
        self.assert_params_for_cmd2(cmd, result)

        # Use Encryption type
        cmd = DEFAULT_CMD +\
            '--emrfs Consistent=true,Encryption=ServerSide,RetryCount=10'
        emf_fs_ba_config = \
            {'Name': 'Setup EMRFS',
             'ScriptBootstrapAction':
                {'Path': ('s3://us-east-1.elasticmapreduce/'
                          'bootstrap-actions/configure-hadoop'),
                 'Args': ['-e',
                          'fs.s3.enableServerSideEncryption=true',
                          '-e',
                          'fs.s3.consistent=true',
                          '-e',
                          'fs.s3.consistent.retryCount=10']
                 }
             }
        result['BootstrapActions'] = [emf_fs_ba_config]
        self.assert_params_for_cmd2(cmd, result)

    def test_emrfs_invalid_encryption_types(self):
        # When no encryption type is specified, only common parameters
        # ['RetryCount', 'RetryPeriod', 'Consistent', 'Args'] are valid
        cmd = DEFAULT_CMD +\
            ('--emrfs RetryCount=5,RetryPeriod=3,Consistent=True,'
             'Args=[fs.s3.sleepTimeSeconds=30],ProviderType=KMS')
        error_msg = ('\naws: error: The parameters provided with the --emrfs '
                     'option are invalid. \n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(error_msg, result[1])

        # Cannot specify both SSE and Encryption Type
        cmd = DEFAULT_CMD + '--emrfs SSE=True,Encryption=ServerSide'
        error_msg = ('\naws: error: The parameters provided with the --emrfs '
                     'option are invalid. \n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(error_msg, result[1])

        cmd = DEFAULT_CMD + '--emrfs SSE=True,Encryption=ClientSide'
        result = self.run_cmd(cmd, 255)
        self.assertEquals(error_msg, result[1])

        # Invalid encryption types
        cmd = DEFAULT_CMD +\
            ('--emrfs Encryption=blahblah')
        error_msg = ('\naws: error: The parameters provided with the --emrfs'
                     ' option are invalid. Encryption type must be either '
                     '"ServerSide" or "ClientSide".\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(error_msg, result[1])

    def test_emrfs_cse_unkown_prodiver(self):
        cmd = DEFAULT_CMD +\
            ('--emrfs Encryption=ClientSide,ProviderType=blah')
        error_msg = ('\naws: error: The encryption provider type "blah" is '
                     'not supported. You must specify one of the following '
                     'client side encryption types: KMS, RSA, or Custom.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(error_msg, result[1])

    def test_emrfs_cse_missing_provider(self):
        cmd = DEFAULT_CMD + '--emrfs Encryption=ClientSide'
        error_msg = ('\naws: error: The following required parameters are '
                     'missing for --emrfs Encryption=ClientSide: '
                     'ProviderType.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(error_msg, result[1])

    def test_emrfs_cse_kms(self):
        cmd = DEFAULT_CMD +\
            ('--emrfs Encryption=ClientSide,ProviderType=kMs,'
             'KeyId=testKMSkey,Consistent=true,RetryCount=3,RetryPeriod=5,'
             'Args=[fs.s3.sleepTimeSeconds=30]')
        result = copy.deepcopy(DEFAULT_RESULT)
        emf_fs_ba_config = \
            {'Name': 'Setup EMRFS',
             'ScriptBootstrapAction':
                {'Path': ('s3://us-east-1.elasticmapreduce/'
                          'bootstrap-actions/configure-hadoop'),
                 'Args': ['-e',
                          'fs.s3.cse.enabled=true',
                          '-e',
                          'fs.s3.cse.encryptionMaterialsProvider='
                          'com.amazon.ws.emr.hadoop.fs.cse.'
                          'KMSEncryptionMaterialsProvider',
                          '-e',
                          'fs.s3.cse.kms.keyId=testKMSkey',
                          '-e',
                          'fs.s3.consistent=true',
                          '-e',
                          'fs.s3.consistent.retryCount=3',
                          '-e',
                          'fs.s3.consistent.retryPeriodSeconds=5',
                          '-e',
                          'fs.s3.sleepTimeSeconds=30']
                 }
             }
        result['BootstrapActions'] = [emf_fs_ba_config]
        self.assert_params_for_cmd2(cmd, result)

    def test_emrfs_cse_kms_parameter_validation(self):
        # Validate KMS provider required parameters
        cmd = DEFAULT_CMD +\
            ('--emrfs Encryption=ClientSide,ProviderType=kMS')
        error_msg = ('\naws: error: The following required parameters '
                     'are missing for --emrfs Encryption=ClientSide,'
                     'ProviderType=KMS: KeyId.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(error_msg, result[1])

        # Validate KMS provider related parameters
        cmd = DEFAULT_CMD +\
            ('--emrfs Encryption=ClientSide,ProviderType=kms,'
             'KeyId=testkey,RSAKeyPairName=blah')
        error_msg = ('\naws: error: The parameters provided with the --emrfs '
                     'option are invalid. You must specify an AWS KMS KeyId '
                     'when using EMRFS client-side encryption with '
                     'ProviderType=KMS.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(error_msg, result[1])

    def test_emrfs_cse_rsa(self):
        cmd = DEFAULT_CMD +\
            ('--emrfs Encryption=ClientSide,ProviderType=Rsa,'
             'PrivateKey=s3://mytest/privatekey,PublicKey='
             's3://mytest/publickey,RSAKeyPairName=myrsakeypair,'
             'Consistent=true,RetryCount=3,RetryPeriod=5,'
             'Args=[fs.s3.sleepTimeSeconds=30]')
        result = copy.deepcopy(DEFAULT_RESULT)
        emf_fs_ba_config = \
            {'Name': 'Setup EMRFS',
             'ScriptBootstrapAction':
                {'Path': ('s3://us-east-1.elasticmapreduce/'
                          'bootstrap-actions/configure-hadoop'),
                 'Args': ['-e',
                          'fs.s3.cse.enabled=true',
                          '-e',
                          'fs.s3.cse.encryptionMaterialsProvider='
                          'com.amazon.ws.emr.hadoop.fs.cse.'
                          'RSAEncryptionMaterialsProvider',
                          '-e',
                          'fs.s3.cse.rsa.private=s3://mytest/privatekey',
                          '-e',
                          'fs.s3.cse.rsa.public=s3://mytest/publickey',
                          '-e',
                          'fs.s3.cse.rsa.name=myrsakeypair',
                          '-e',
                          'fs.s3.consistent=true',
                          '-e',
                          'fs.s3.consistent.retryCount=3',
                          '-e',
                          'fs.s3.consistent.retryPeriodSeconds=5',
                          '-e',
                          'fs.s3.sleepTimeSeconds=30']
                 }
             }
        result['BootstrapActions'] = [emf_fs_ba_config]
        self.assert_params_for_cmd2(cmd, result)

    def test_emrfs_cse_rsa_validation(self):
        # Validate required parameters
        cmd = DEFAULT_CMD +\
            ('--emrfs Encryption=ClientSide,ProviderType=rsa')
        error_msg = ('\naws: error: The following required parameters are '
                     'missing for --emrfs Encryption=ClientSide,'
                     'ProviderType=RSA: PrivateKey.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(error_msg, result[1])

        cmd = DEFAULT_CMD + ('--emrfs Encryption=ClientSide,ProviderType=RSA,'
                             'PrivateKey=s3://test/privatekey')
        error_msg = ('\naws: error: The following required parameters are '
                     'missing for --emrfs Encryption=ClientSide,'
                     'ProviderType=RSA: PublicKey.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(error_msg, result[1])

        cmd = DEFAULT_CMD + ('--emrfs Encryption=ClientSide,ProviderType=RSA,'
                             'PrivateKey=s3://test/privatekey,'
                             'PublicKey=s3://test/publickey')
        error_msg = ('\naws: error: The following required parameters are '
                     'missing for --emrfs Encryption=ClientSide,'
                     'ProviderType=RSA: RSAKeyPairName.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(error_msg, result[1])

        # Validate RSA provider related parameters
        cmd = DEFAULT_CMD +\
            ('--emrfs Encryption=ClientSide,ProviderType=Rsa,PrivateKey='
             's3://test/privatekey,PublicKey=s3://test/publickey,'
             'RSAKeyPairName=rsaKey,KeyId=blah')
        error_msg = ('\naws: error: The parameters provided with the --emrfs '
                     'option are invalid. You must specify a PrivateKey, '
                     'PublicKey and RSAKeyPairName when using EMRFS '
                     'client-side encryption with ProviderType=RSA.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(error_msg, result[1])

    def test_emrfs_cse_custom(self):
        cmd = DEFAULT_CMD +\
            ('--emrfs Encryption=ClientSide,ProviderType=cusTOM,'
             'ProviderLocation=s3://test/provider,ProviderClassName'
             '=customproviderclass,Consistent=true,RetryCount=3,RetryPeriod=5,'
             'Args=[fs.s3.sleepTimeSeconds=30]')
        result = copy.deepcopy(DEFAULT_RESULT)
        result['BootstrapActions'] = \
            [{'Name': 'S3 get',
              'ScriptBootstrapAction':
                {'Path': 'file:/usr/share/aws/emr/scripts/s3get',
                 'Args': ['-s',
                          's3://test/provider',
                          '-d',
                          '/usr/share/aws/emr/auxlib',
                          '-f'
                          ]
                 }

              },
             {'Name': 'Setup EMRFS',
              'ScriptBootstrapAction':
                {'Path': ('s3://us-east-1.elasticmapreduce/'
                          'bootstrap-actions/configure-hadoop'),
                 'Args': ['-e',
                          'fs.s3.cse.enabled=true',
                          '-e',
                          'fs.s3.cse.encryptionMaterialsProvider'
                          '=customproviderclass',
                          '-e',
                          'fs.s3.consistent=true',
                          '-e',
                          'fs.s3.consistent.retryCount=3',
                          '-e',
                          'fs.s3.consistent.retryPeriodSeconds=5',
                          '-e',
                          'fs.s3.sleepTimeSeconds=30']
                 }
              }
             ]
        self.assert_params_for_cmd2(cmd, result)

    def test_emrfs_cse_custom_validations(self):
        # Validate CUSTOM provider required parameters
        cmd = DEFAULT_CMD +\
            ('--emrfs Encryption=ClientSide,ProviderType=Custom')
        error_msg = ('\naws: error: The following required parameters '
                     'are missing for --emrfs Encryption=ClientSide,'
                     'ProviderType=CUSTOM: ProviderLocation.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(error_msg, result[1])

        cmd = DEFAULT_CMD +\
            ('--emrfs Encryption=ClientSide,ProviderType=Custom,'
             'ProviderClassName=providerclass')
        error_msg = ('\naws: error: The following required parameters '
                     'are missing for --emrfs Encryption=ClientSide,'
                     'ProviderType=CUSTOM: ProviderLocation.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(error_msg, result[1])

        cmd = DEFAULT_CMD +\
            ('--emrfs Encryption=ClientSide,ProviderType=Custom,'
             'ProviderLocation=s3://test/customprovider')
        error_msg = ('\naws: error: The following required parameters are '
                     'missing for --emrfs Encryption=ClientSide,'
                     'ProviderType=CUSTOM: ProviderClassName.\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(error_msg, result[1])

        # Validate CUSTOM provider related parameters
        cmd = DEFAULT_CMD +\
            ('--emrfs Encryption=ClientSide,ProviderType=cuSTOM,'
             'ProviderLocation=s3://test/customprovider,'
             'ProviderClassName=providerclassPrivateKey='
             's3://test/privatekey,PublicKey=s3://test/publickey')
        error_msg = ('\naws: error: The parameters provided with the --emrfs '
                     'option are invalid. You must specify a ProviderLocation'
                     ' and ProviderClassName when using EMRFS client-side '
                     'encryption with ProviderType=CUSTOM\n')
        result = self.run_cmd(cmd, 255)
        self.assertEquals(error_msg, result[1])

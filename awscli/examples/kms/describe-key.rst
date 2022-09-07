**To find detailed information about a KMS key**

The following ``describe-key`` example gets detailed information about the AWS managed key for Amazon S3 in the example account and Region. You can use this command to find details about AWS managed keys and customer managed keys. 

To specify the KMS key, use the ``key-id`` parameter. This example uses an alias name value, but you can use a key ID, key ARN, alias name, or alias ARN in this command. ::

    aws kms describe-key \
        --key-id alias/aws/s3

Output::

    {
        "KeyMetadata": {
            "AWSAccountId": "111122223333",
            "KeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
            "Arn": "arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab",
            "CreationDate": "2019-08-23T00:06:23.394000+00:00",
            "Enabled": true,
            "Description": "Default KMS key that protects my S3 objects when no other key is defined",
            "KeyUsage": "ENCRYPT_DECRYPT",
            "KeyState": "Enabled",
            "Origin": "AWS_KMS",
            "KeyManager": "AWS",
            "CustomerMasterKeySpec": "SYMMETRIC_DEFAULT",
            "KeySpec": "SYMMETRIC_DEFAULT",
            "EncryptionAlgorithms": [
                "SYMMETRIC_DEFAULT"
            ],
            "MultiRegion": false
        }
    }

For more information, see `Viewing keys <https://docs.aws.amazon.com/kms/latest/developerguide/viewing-keys.html>`__ in the *AWS Key Management Service Developer Guide*.

**To get details about an RSA asymmetric KMS key**

The following ``describe-key`` example gets detailed information about an asymmetric RSA KMS key used for signing and verification. ::

    aws kms describe-key \
        --key-id 1234abcd-12ab-34cd-56ef-1234567890ab

Output::

    {
        "KeyMetadata": {
            "AWSAccountId": "111122223333",
            "KeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
            "Arn": "arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab",
            "CreationDate": "2021-01-29T16:37:28.915000+00:00",
            "Enabled": false,
            "Description": "",
            "KeyUsage": "SIGN_VERIFY",        
            "KeyState": "Disabled",
            "Origin": "AWS_KMS",
            "KeyManager": "CUSTOMER",
            "CustomerMasterKeySpec": "RSA_2048",
            "KeySpec": "RSA_2048",    
            "SigningAlgorithms": [
                "RSASSA_PKCS1_V1_5_SHA_256",
                "RSASSA_PKCS1_V1_5_SHA_384",
                "RSASSA_PKCS1_V1_5_SHA_512",
                "RSASSA_PSS_SHA_256",
                "RSASSA_PSS_SHA_384",
                "RSASSA_PSS_SHA_512"
            ],
            "MultiRegion": false
        }
    }    
    
For more information, see `Identifying asymmetric KMS keys <https://docs.aws.amazon.com/kms/latest/developerguide/find-symm-asymm.html>`__ in the *AWS Key Management Service Developer Guide*.

**To get details about a multi-Region replica key**

The following ``describe-key`` example gets metadata for a multi-Region replica key. This multi-Region key is a symmetric encryption key. The output of a ``describe-key`` command for any multi-Region key returns information about the primary key and all of its replicas. ::

    aws kms describe-key \
        --key-id arn:aws:kms:ap-northeast-1:111122223333:key/mrk-1234abcd12ab34cd56ef1234567890ab

Output::

    {
        "KeyMetadata": {
            "AWSAccountId": "111122223333",
            "KeyId": "mrk-1234abcd12ab34cd56ef1234567890ab",
            "Arn": "arn:aws:kms:ap-northeast-1:111122223333:key/mrk-1234abcd12ab34cd56ef1234567890ab",
            "CreationDate": "2022-06-28T21:09:15.849000+00:00",
            "Enabled": true,
            "Description": "",
            "KeyUsage": "ENCRYPT_DECRYPT",
            "KeyState": "Enabled",
            "Origin": "AWS_KMS",
            "KeyManager": "CUSTOMER",
            "CustomerMasterKeySpec": "SYMMETRIC_DEFAULT",
            "KeySpec": "SYMMETRIC_DEFAULT",
            "EncryptionAlgorithms": [
                "SYMMETRIC_DEFAULT"
            ],
            "MultiRegion": true,
            "MultiRegionConfiguration": {
                "MultiRegionKeyType": "PRIMARY",
                "PrimaryKey": {
                    "Arn": "arn:aws:kms:us-west-2:111122223333:key/mrk-1234abcd12ab34cd56ef1234567890ab",
                    "Region": "us-west-2"
                },
                "ReplicaKeys": [
                    {
                        "Arn": "arn:aws:kms:eu-west-1:111122223333:key/mrk-1234abcd12ab34cd56ef1234567890ab",
                        "Region": "eu-west-1"
                    },
                    {
                        "Arn": "arn:aws:kms:ap-northeast-1:111122223333:key/mrk-1234abcd12ab34cd56ef1234567890ab",
                        "Region": "ap-northeast-1"
                    },
                    {
                        "Arn": "arn:aws:kms:sa-east-1:111122223333:key/mrk-1234abcd12ab34cd56ef1234567890ab",
                        "Region": "sa-east-1"
                    }
                ]
            }
        }
    }

For more information, see `Viewing multi-Region keys <https://docs.aws.amazon.com/kms/latest/developerguide/multi-region-keys-view.html>`__ in the *AWS Key Management Service Developer Guide*.

**To get details about an HMAC KMS key**

The following ``describe-key`` example gets detailed information about an HMAC KMS key. ::
        
    aws kms describe-key \
        --key-id 1234abcd-12ab-34cd-56ef-1234567890ab

Output::

    {
        "KeyMetadata": {
            "AWSAccountId": "111122223333",
            "KeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
            "Arn": "arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab",
            "CreationDate": 1566160362.664,
            "Enabled": true,
            "Description": "Test key",
            "KeyUsage": "GENERATE_VERIFY_MAC",
            "KeyState": "Enabled",
            "Origin": "AWS_KMS",
            "KeyManager": "CUSTOMER",
            "CustomerMasterKeySpec": "HMAC_256",
            "KeySpec": "HMAC_256",
            "MacAlgorithms": [
                "HMAC_SHA_256"
            ],
            "MultiRegion": false
        }
    }

For more information, see `Viewing HMAC KMS keys <https://docs.aws.amazon.com/kms/latest/developerguide/hmac-view.html>`__ in the *AWS Key Management Service Developer Guide*.    
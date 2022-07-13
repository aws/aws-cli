**To find detailed information about a KMS key**

The following ``describe-key`` example gets detailed information about the AWS managed key for Amazon S3 in the example account and Region. You can use this command to find details about AWS managed keys and customer managed keys. 

To specify the KMS key, use the ``key-id`` parameter. This example uses an alias name value, but you can use a key ID, key ARN, alias name, or alias ARN in this command. ::

    aws kms describe-key \
        --key-id alias/aws/s3

Output::

    {
        "KeyMetadata": {
            "AWSAccountId": "846764612917",
            "KeyId": "b8a9477d-836c-491f-857e-07937918959b",
            "Arn": "arn:aws:kms:us-west-2:846764612917:key/b8a9477d-836c-491f-857e-07937918959b",
            "CreationDate": 1566518783.394,
            "Enabled": true,
            "Description": "Default KMS key that protects my S3 objects when no other key is defined",
            "KeyUsage": "ENCRYPT_DECRYPT",
            "KeyState": "Enabled",
            "Origin": "AWS_KMS",
            "KeyManager": "AWS",
            "CustomerMasterKeySpec": "SYMMETRIC_DEFAULT",
            "EncryptionAlgorithms": [
                "SYMMETRIC_DEFAULT"
            ]
        }
    }

For more information, see `Viewing keys <https://docs.aws.amazon.com/kms/latest/developerguide/viewing-keys.html>`__ in the *AWS Key Management Service Developer Guide*.

**To get details about an RSA asymmetric KMS key**

The following ``describe-key`` example gets detailed information about an asymmetric RSA KMS key used for signing and verification. ::

    aws kms describe-key \
        --key-id 1234abcd-12ab-34cd-56ef-1234567890ab

Output::

    {
        "AWSAccountId": "111122223333",
        "KeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        "Arn": "arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab",
        "CreationDate": 1571767572.317,
        "CustomerMasterKeySpec": "RSA_2048",
        "Enabled": false,
        "Description": "",
        "KeyState": "Disabled",
        "Origin": "AWS_KMS",
        "MultiRegion": false,
        "KeyManager": "CUSTOMER",
        "KeySpec": "RSA_2048",
        "KeyUsage": "SIGN_VERIFY",
        "SigningAlgorithms": [
          "RSASSA_PKCS1_V1_5_SHA_256",
          "RSASSA_PKCS1_V1_5_SHA_384",
          "RSASSA_PKCS1_V1_5_SHA_512",
          "RSASSA_PSS_SHA_256",
          "RSASSA_PSS_SHA_384",
          "RSASSA_PSS_SHA_512"
        ]
      }
    }

**To get details about a multi-Region replica key**

The following ``describe-key`` example gets metadata for a multi-Region replica key. This multi-Region key is a symmetric encryption key. The output of a ``describe-key`` command for any multi-Region key returns information about the primary key and all of its replicas. ::

    aws kms describe-key \
        --key-id arn:aws:kms:ap-northeast-1:111122223333:key/mrk-1234abcd12ab34cd56ef1234567890ab

Output::

    {
      "KeyMetadata": {
        "MultiRegion": true,
        "AWSAccountId": "111122223333",
        "Arn": "arn:aws:kms:ap-northeast-1:111122223333:key/mrk-1234abcd12ab34cd56ef1234567890ab",
        "CreationDate": 1586329200.918,
        "Description": "",
        "Enabled": true,
        "KeyId": "mrk-1234abcd12ab34cd56ef1234567890ab",
        "KeyManager": "CUSTOMER",
        "KeyState": "Enabled",
        "KeyUsage": "ENCRYPT_DECRYPT",
        "Origin": "AWS_KMS",
        "CustomerMasterKeySpec": "SYMMETRIC_DEFAULT",
        "EncryptionAlgorithms": [
          "SYMMETRIC_DEFAULT"
        ],
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

**To get details about an HMAC KMS key**

The following ``describe-key`` example gets detailed information about an HMAC KMS key. ::
        
    aws kms describe-key \
        --key-id 1234abcd-12ab-34cd-56ef-1234567890ab

Output::

    {
      "KeyMetadata": {
        "AWSAccountId": "123456789012",
        "KeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        "Arn": "arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab",
        "CreationDate": 1566160362.664,
        "Enabled": true,
        "Description": "Test key",
        "KeyUsage": "GENERATE_VERIFY_MAC",
        "KeyState": "Enabled",
        "Origin": "AWS_KMS",
        "KeyManager": "CUSTOMER",
        "CustomerMasterKeySpec": "HMAC_256",
        "MacAlgorithms": [
          "HMAC_SHA_256"
        ],
        "MultiRegion": false
      }
    }
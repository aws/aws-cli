**To create a customer managed KMS key in AWS KMS**

The following ``create-key`` example creates a symmetric encryption KMS key.

* To create the basic KMS key, a symmetric encryption key, you do not need to specify the ``key-spec`` or ``key-usage`` parameters. The default values for those parameters create a symmetric encryption key.
* The ``--tags`` parameter uses shorthand syntax to add a tag with a key name ``Purpose`` and value of ``Test``. For information about using shorthand syntax, see `Using Shorthand Syntax with the AWS Command Line Interface <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-shorthand.html>`__ in the *AWS CLI User Guide*.
* The ``--description parameter`` adds an optional description.

Because this command doesn't specify a key policy, the KMS key gets the `default key policy <https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html#key-policy-default>`__ for programmatically created KMS keys. To view the key policy, use the ``get-key-policy`` command. To change the key policy, use the ``put-key-policy`` command. ::

    aws kms create-key \
        --tags TagKey=Purpose,TagValue=Test \
        --description "Test key"

The ``create-key`` command returns the key metadata, including the key ID and ARN of the new KMS key. You can use these values to identify the KMS key in other AWS KMS operations. The output does not include the tags. To view the tags for a KMS key, use the ``list-resource-tags command``. 

Output::

    {
        "KeyMetadata": {
            "Origin": "AWS_KMS",
            "KeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
            "Description": "Test key",
            "KeyManager": "CUSTOMER",
            "Enabled": true,
            "KeySpec": "SYMMETRIC_DEFAULT",
            "CustomerMasterKeySpec": "SYMMETRIC_DEFAULT",
            "KeyUsage": "ENCRYPT_DECRYPT",
            "KeyState": "Enabled",
            "CreationDate": 1502910355.475,
            "Arn": "arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab",
            "AWSAccountId": "111122223333",
            "MultiRegion": false
            "EncryptionAlgorithms": [
                "SYMMETRIC_DEFAULT"
            ],
        }
    }

Note: The ``create-key`` command does not let you specify an alias, To create an alias for the new KMS key, use the ``create-alias`` command.

For more information, see `Creating keys <https://docs.aws.amazon.com/kms/latest/developerguide/create-keys.html>`__ in the *AWS Key Management Service Developer Guide*.

**Example 2: To create an asymmetric RSA KMS key for encryption and decryption**

The following ``create-key`` example creates a KMS key that contains an asymmetric RSA key pair for encryption and decryption. ::

    aws kms create-key \
       --key-spec RSA_4096 \
       --key-usage ENCRYPT_DECRYPT

Output::

    {
      "KeyMetadata": {
        "Arn": "arn:aws:kms:us-east-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab",
        "AWSAccountId": "111122223333",
        "CreationDate": "2021-04-05T14:04:55-07:00",
        "CustomerMasterKeySpec": "RSA_4096",
        "Description": "",
        "Enabled": true,
        "EncryptionAlgorithms": [
          "RSAES_OAEP_SHA_1",
          "RSAES_OAEP_SHA_256"
        ],
        "KeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        "KeyManager": "CUSTOMER",
        "KeySpec": "RSA_4096",
        "KeyState": "Enabled",
        "KeyUsage": "ENCRYPT_DECRYPT",
        "MultiRegion": false,
        "Origin": "AWS_KMS"
      }
    }

For more information, see `Asymmetric keys in AWS KMS <https://docs.aws.amazon.com/kms/latest/developerguide/symmetric-asymmetric.html>`__ in the *AWS Key Management Service Developer Guide*.

**Example 3: To create an asymmetric elliptic curve KMS key for signing and verification**

To create an HMAC KMS key that contains an asymmetric elliptic curve (ECC) key pair for signing and verification. The ``--key-usage`` parameter is required even though ``SIGN_VERIFY`` is the only valid value for ECC KMS keys. ::

    aws kms create-key \
        --key-spec ECC_NIST_P521 \
        --key-usage SIGN_VERIFY

Output::

     {
      "KeyMetadata": {
        "Arn": "arn:aws:kms:us-east-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab",
        "AWSAccountId": "111122223333",
        "CreationDate": "2019-12-02T07:48:55-07:00",
        "CustomerMasterKeySpec": "ECC_NIST_P521",
        "Description": "",
        "Enabled": true,
        "KeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        "KeyManager": "CUSTOMER",
        "KeySpec": "ECC_NIST_P521",
        "KeyState": "Enabled",
        "KeyUsage": "SIGN_VERIFY",
        "MultiRegion": false,
        "Origin": "AWS_KMS",
        "SigningAlgorithms": [
          "ECDSA_SHA_512"
        ]
      }
    }       

**Example 4: To create an HMAC KMS key**

The following ``create-key`` example creates a 384-bit symmetric HMAC KMS key. The ```GENERATE_VERIFY_MAC`` value for the ``--key-usage`` parameter is required even though it's the only valid value for HMAC KMS keys. ::

    aws kms create-key \
        --key-spec HMAC_384 \
        --key-usage GENERATE_VERIFY_MAC

Output::

    {
      "KeyMetadata": {
        "Arn": "arn:aws:kms:us-east-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab",
        "AWSAccountId": "111122223333",
        "CreationDate": "2022-04-05T14:04:55-07:00",
        "CustomerMasterKeySpec": "HMAC_384",
        "Description": "",
        "Enabled": true,
        "KeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        "KeyManager": "CUSTOMER",
        "KeySpec": "HMAC_384",
        "KeyState": "Enabled",
        "KeyUsage": "GENERATE_VERIFY_MAC",
        "MacAlgorithms": [
          "HMAC_SHA_384"
        ],
        "MultiRegion": false,
        "Origin": "AWS_KMS"
      }
    }

**Example 4: To create a multi-Region primary KMS key**

The following ``create-key`` example creates a multi-Region primary symmetric encryption key. Because the default values for all parameters create a symmetric encryption key, only the ``--multi-region`` parameter is required for this KMS key. In the AWS CLI, to indicate that a Boolean parameter is true, just specify the parameter name. ::

    aws kms create-key \
        --multi-region

Output::

    {
      "KeyMetadata": {
        "Arn": "arn:aws:kms:us-west-2:111122223333:key/mrk-1234abcd12ab34cd56ef12345678990ab",
        "AWSAccountId": "111122223333",
        "CreationDate": "2021-09-02T016:15:21-09:00",
        "CustomerMasterKeySpec": "SYMMETRIC_DEFAULT",
        "Description": "",
        "Enabled": true,
        "EncryptionAlgorithms": [
          "SYMMETRIC_DEFAULT"
        ],
        "KeyId": "mrk-1234abcd12ab34cd56ef12345678990ab",
        "KeyManager": "CUSTOMER",
        "KeySpec": "SYMMETRIC_DEFAULT",
        "KeyState": "Enabled",
        "KeyUsage": "ENCRYPT_DECRYPT",
        "MultiRegion": true,
        "MultiRegionConfiguration": {
          "MultiRegionKeyType": "PRIMARY",
          "PrimaryKey": {
            "Arn": "arn:aws:kms:us-west-2:111122223333:key/mrk-1234abcd12ab34cd56ef12345678990ab",
            "Region": "us-west-2"
          },
          "ReplicaKeys": []
        },
        "Origin": "AWS_KMS"
      }
    }

**Example 5: To create a KMS key for imported key material**

The following ``create-key`` example creates a creates a KMS key with no key material. When the operation is complete, you can import your own key material into the KMS key. To create this KMS key, set the ``--origin`` parameter to ``EXTERNAL``. ::

    aws kms create-key \
        --origin EXTERNAL

Output::

   {
      "KeyMetadata": {
        "Arn": "arn:aws:kms:us-east-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab",
        "AWSAccountId": "111122223333",
        "CreationDate": "2019-12-02T07:48:55-07:00",
        "CustomerMasterKeySpec": "SYMMETRIC_DEFAULT",
        "Description": "",
        "Enabled": false,
        "EncryptionAlgorithms": [
          "SYMMETRIC_DEFAULT"
        ],
        "KeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        "KeyManager": "CUSTOMER",
        "KeySpec": "SYMMETRIC_DEFAULT",
        "KeyState": "PendingImport",
        "KeyUsage": "ENCRYPT_DECRYPT",
        "MultiRegion": false,
        "Origin": "EXTERNAL"
      }
    }


**Example 6: To create a KMS key in an AWS CloudHSM custom key store**

The following ``create-key`` example creates a creates a KMS key in the specified AWS CloudHSM custom key store. The operation creates the KMS key and its metadata in AWS KMS and creates the key material in the AWS CloudHSM cluster associated with the custom key store. The ``--custom-key-store-id`` and ``--origin`` parameters are required. ::

    aws kms create-key \
        --origin AWS_CLOUDHSM \
        --custom-key-store-id cks-1234567890abcdef0

Output::

    {
      "KeyMetadata": {
        "Arn": "arn:aws:kms:us-east-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab",
        "AWSAccountId": "111122223333",
        "CloudHsmClusterId": "cluster-1a23b4cdefg",
        "CreationDate": "2019-12-02T07:48:55-07:00",
        "CustomerMasterKeySpec": "SYMMETRIC_DEFAULT",
        "CustomKeyStoreId": "cks-1234567890abcdef0",
        "Description": "",
        "Enabled": true,
        "EncryptionAlgorithms": [
          "SYMMETRIC_DEFAULT"
        ],
        "KeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
        "KeyManager": "CUSTOMER",
        "KeySpec": "SYMMETRIC_DEFAULT",
        "KeyState": "Enabled",
        "KeyUsage": "ENCRYPT_DECRYPT",
        "MultiRegion": false,
        "Origin": "AWS_CLOUDHSM"
      }
    }

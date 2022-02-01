**To find detailed information about a customer master key (CMK)**

The following ``describe-key`` example gets detailed information about the AWS managed CMK for Amazon S3 in the example account and Region. You can use this command to find details about AWS managed CMKs and customer managed CMKs. 

To specify the CMK, use the ``key-id`` parameter. This example uses an alias name value, but you can use a key ID, key ARN, alias name, or alias ARN in this command. ::

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
            "Description": "Default master key that protects my S3 objects when no other key is defined",
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

For more information, see `Viewing Keys <https://docs.aws.amazon.com/kms/latest/developerguide/viewing-keys.html>`__ in the *AWS Key Management Service Developer Guide*.
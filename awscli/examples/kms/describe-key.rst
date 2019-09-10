**To find detailed information about a customer master key (CMK)**

The following ``describe-key`` example retrieves detailed information about the AWS managed CMK for Amazon S3. 

This example uses an alias name value for the ``--key-id`` parameter, but you can use a key ID, key ARN, alias name, or alias ARN in this command. ::

    aws kms describe-key --key-id alias/aws/s3

Output::

    {
        "KeyMetadata": {
            "Description": "Default master key that protects my S3 objects when no other key is defined",
            "Arn": "arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab",
            "KeyState": "Enabled",
            "Origin": "AWS_KMS",
            "KeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
            "KeyUsage": "ENCRYPT_DECRYPT",
            "AWSAccountId": "123456789012",
            "Enabled": true,
            "KeyManager": "AWS",
            "CreationDate": 1566518783.394
        }
    }

For more information, see `Viewing Keys<https://docs.aws.amazon.com/kms/latest/developerguide/viewing-keys.html>`__ in the *AWS Key Management Service Developer Guide*.
**Example 1: To list all aliases in an AWS account and Region**

The following ``list-aliases`` example lists all aliases in the default Region of the AWS account. The output includes aliases associated with AWS managed KMS keys and customer managed KMS keys. ::

    aws kms list-aliases

Output::

    {
        "Aliases": [
            {
                "AliasArn": "arn:aws:kms:us-west-2:123456789012:alias/testKey",
                "AliasName": "alias/testKey",
                "TargetKeyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            },
            {
                "AliasArn": "arn:aws:kms:us-west-2:123456789012:alias/FinanceDept",
                "AliasName": "alias/FinanceDept",
                "TargetKeyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            },
            {
                "AliasArn": "arn:aws:kms:us-west-2:123456789012:alias/aws/dynamodb",
                "AliasName": "alias/aws/dynamodb",
                "TargetKeyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
            },
            {
                "AliasArn": "arn:aws:kms:us-west-2:123456789012:alias/aws/ebs",
                "AliasName": "alias/aws/ebs",
                "TargetKeyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"
            }
        ]
    }

**Example 2: To list all aliases for a particular KMS key**

The following ``list-aliases`` example uses the ``key-id`` parameter to list all aliases that are associated with a particular KMS key.

Each alias is associated with only one KMS key, but a KMS key can have multiple aliases. This command is very useful because the AWS KMS console lists only one alias for each KMS key. To find all aliases for a KMS key, you must use the ``list-aliases`` command.

This example uses the key ID of the KMS key for the ``--key-id`` parameter, but you can use a key ID, key ARN, alias name, or alias ARN in this command. ::

    aws kms list-aliases \
        --key-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "Aliases": [
            {
                "TargetKeyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "AliasArn": "arn:aws:kms:us-west-2:123456789012:alias/oregon-test-key",
                "AliasName": "alias/oregon-test-key"
            },
            {
                "TargetKeyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "AliasArn": "arn:aws:kms:us-west-2:123456789012:alias/project121-test",
                "AliasName": "alias/project121-test"
            }
        ]
    }

For more information, see `Aliases in AWS KMS <https://docs.aws.amazon.com/kms/latest/developerguide/kms-alias.html>`__ in the *AWS Key Management Service Developer Guide*.
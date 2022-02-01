**To create a customer managed CMK in AWS KMS**

The following ``create-key`` example creates a customer managed CMK.

* The ``--tags`` parameter uses shorthand syntax to add a tag with a key name ``Purpose`` and value of ``Test``. For information about using shorthand syntax, see `Using Shorthand Syntax with the AWS Command Line Interface <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-shorthand.html>`__ in the *AWS CLI User Guide*.
* The ``--description parameter`` adds an optional description.

Because this doesn't specify a policy, the CMK gets the `default key policy <https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html#key-policy-default>__. To view the key policy, use the ``get-key-policy`` command. To change the key policy, use the ``put-key-policy`` command. ::

    aws kms create-key \
        --tags TagKey=Purpose,TagValue=Test \
        --description "Development test key"

The ``create-key`` command returns the key metadata, including the key ID and ARN of the new CMK. You can use these values to identify the CMK to other AWS KMS operations. The output does not include the tags. To view the tags for a CMK, use the ``list-resource-tags command``. ::

    {
        "KeyMetadata": {
            "AWSAccountId": "123456789012",
            "KeyId": "1234abcd-12ab-34cd-56ef-1234567890ab",
            "Arn": "arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab",
            "CreationDate": 1566160362.664,
            "Enabled": true,
            "Description": "Development test key",
            "KeyUsage": "ENCRYPT_DECRYPT",
            "KeyState": "Enabled",
            "Origin": "AWS_KMS",
            "KeyManager": "CUSTOMER"
        }
    }

Note: The ``create-key`` command does not let you specify an alias, To create an alias that points to the new CMK, use the ``create-alias`` command.

For more information, see `Creating Keys <https://docs.aws.amazon.com/kms/latest/developerguide/create-keys.html>`__ in the *AWS Key Management Service Developer Guide*.

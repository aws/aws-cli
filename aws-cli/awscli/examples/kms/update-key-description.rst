**Example 1: To add or change a description to a customer managed KMS key**

The following ``update-key-description`` example adds a description to a customer managed KMS key. You can use the same command to change an existing description. 

* The ``--key-id`` parameter identifies the KMS key in the command. This example uses a key ARN value, but you can use either the key ID or the key ARN of the KMS key. 
* The ``--description`` parameter specifies the new description. The value of this parameter replaces the current description of the KMS key, if any. ::

    aws kms update-key-description \
        --key-id arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --description "IT Department test key"

This command produces no output. To view the description of a KMS key, use the ``describe-key`` command. 

For more information, see `Access and list KMS key details <https://docs.aws.amazon.com/kms/latest/developerguide/finding-keys.html>`__ in the *AWS Key Management Service Developer Guide*.

**Example 2: To delete the description of a customer managed KMS key**

The following ``update-key-description`` example deletes the description to a customer managed KMS key.

* The ``--key-id`` parameter identifies the KMS key in the command. This example uses a key ID value, but you can use either the key ID or the key ARN of the KMS key. 
* The ``--description`` parameter with an empty string value ('') deletes the existing description. ::

    aws kms update-key-description \
        --key-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --description ''

This command produces no output. To view the description of a KMS key, use the the describe-key command.

For more information, see `Access and list KMS key details <https://docs.aws.amazon.com/kms/latest/developerguide/finding-keys.html>`__ in the *AWS Key Management Service Developer Guide*.
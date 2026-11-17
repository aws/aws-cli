**To copy a key policy from one KMS key to another KMS key**

The following ``get-key-policy`` example gets the key policy from one KMS key and saves it in a text file. Then, it replaces the policy of a different KMS key using the text file as the policy input.

Because the ``--policy`` parameter of ``put-key-policy`` requires a string, you must use the ``--output text`` option to return the output as a text string instead of JSON. ::

    aws kms get-key-policy \
        --policy-name default \
        --key-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --query Policy \
        --output text > policy.txt

The following ``put-key-policy`` example uses the ``policy.txt`` file to replace the key policy of the other KMS key. ::

    aws kms put-key-policy \
        --policy-name default \
        --key-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --policy file://policy.txt

Contents of ``policy.txt``::

    {
        "Version": "2012-10-17",
        "Id": "key-default-1",
        "Statement": [
            {
                "Sid": "Enable IAM User Permissions",
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::123456789012:root"
                },
                "Action": "kms:*",
                "Resource": "*"
            }
        ]
    }

This command produces no output.

For more information, see `Key policies in AWS KMS <https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html>`__ in the *AWS Key Management Service Developer Guide*.

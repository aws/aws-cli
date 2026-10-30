**To get the KMS keys in an account and Region**

The following ``list-keys`` example gets the KMS keys in an account and Region. This command returns both AWS managed keys and customer managed keys. ::

    aws kms list-keys 

Output::

    {
        "Keys": [
            {
                "KeyArn": "arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "KeyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            },
            {
                "KeyArn": "arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "KeyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            },
            {
                "KeyArn": "arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "KeyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
            }
        ]    
    }

For more information, see `Viewing Keys <https://docs.aws.amazon.com/kms/latest/developerguide/viewing-keys.html>`__ in the *AWS Key Management Service Developer Guide*.
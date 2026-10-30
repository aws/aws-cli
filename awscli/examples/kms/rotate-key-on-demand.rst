**To perform on-demand rotation of a KMS key**

The following ``rotate-key-on-demand`` example immediately initiates rotation of the key material for the specified KMS key. ::

    aws kms rotate-key-on-demand \
        --key-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "KeyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `How to perform on-demand key rotation <https://docs.aws.amazon.com/kms/latest/developerguide/rotating-keys-on-demand.html>`__ in the *AWS Key Management Service Developer Guide*.

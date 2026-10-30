**To temporarily disable a KMS key**

The following ``disable-key`` example disables a customer managed KMS key. To re-enable the KMS key, use the ``enable-key`` command. ::

    aws kms disable-key \
        --key-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output.

For more information, see `Enabling and Disabling Keys <https://docs.aws.amazon.com/kms/latest/developerguide/enabling-keys.html>`__ in the *AWS Key Management Service Developer Guide*.
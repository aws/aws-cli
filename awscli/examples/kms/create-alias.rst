**To create an alias for a KMS key**

The following ``create-alias`` example creates an alias named ``example-alias`` for the KMS key identified by key ID ``a1b2c3d4-5678-90ab-cdef-EXAMPLE11111``.

Alias names must begin with ``alias/``. Do not use alias names that begin with ``alias/aws``; these are reserved for use by AWS. ::

    aws kms create-alias \
        --alias-name alias/example-alias \
        --target-key-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output. To see the new alias, use the ``list-aliases`` command. 

For more information, see `Using aliases <https://docs.aws.amazon.com/kms/latest/developerguide/kms-alias.html>`__ in the *AWS Key Management Service Developer Guide*.

**To revoke a grant on a customer master key**

The following ``revoke-grant`` example deletes a grant from a KMS key. The following example command specifies the ``grant-id`` and the ``key-id`` parameters. The value of the ``key-id`` parameter can be the key ID or key ARN of the KMS key. ::

    aws kms revoke-grant \
        --grant-id 1234a2345b8a4e350500d432bccf8ecd6506710e1391880c4f7f7140160c9af3 \
        --key-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output. To confirm that the grant was revoked, use the ``list-grants`` command.

For more information, see `Retiring and revoking grants <https://docs.aws.amazon.com/kms/latest/developerguide/grant-delete.html>`__ in the *AWS Key Management Service Developer Guide*.
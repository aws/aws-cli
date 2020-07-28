**To revoke a grant on a customer master key**

The following ``revoke-grant`` example deletes a grant from a CMK. The following example command specifies the ``grant-id`` and the ``key-id`` parameters. The value of the ``key-id`` parameter can be the key ID or the Amazon Resource Name (ARN) of the CMK. ::

    aws kms revoke-grant \
        --grant-id 1234a2345b8a4e350500d432bccf8ecd6506710e1391880c4f7f7140160c9af3 \
        --key-id 1234abcd-12ab-34cd-56ef-1234567890ab

This command produces no output. To confirm that the grant was revoked, use the ``list-grants`` command.

For more information, see `Using Grants <https://docs.aws.amazon.com/kms/latest/developerguide/grants.html>`__ in the *AWS Key Management Service Developer Guide*.
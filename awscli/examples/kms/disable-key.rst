**To temporarily disable a customer master key (CMK)**

The following example uses the ``disable-key`` command to disable a customer managed CMK. You can use a command like this one to prevent the CMK from being used in cryptographic operations. Disabling is always temporary. To re-enable the CMK, use the ``enable-key`` command. 

To specify the CMK, use the ``key-id`` parameter. This example uses an key ID value, but you can use a key ID or key ARN value in this command. Before running this command, replace the example key ID with a valid one. ::

    aws kms enable-key \
        --key-id 1234abcd-12ab-34cd-56ef-1234567890ab

This command produces no output.

For more information, see `Enabling and Disabling Keys <https://docs.aws.amazon.com/kms/latest/developerguide/enabling-keys.html>`__ in the *AWS Key Management Service Developer Guide*.
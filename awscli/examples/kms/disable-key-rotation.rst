**To disable automatic rotation of a customer master key (CMK)**

The following ``disable-key-rotation`` example disables automatic rotation of a customer managed CMK. To reenable automatic rotation, use the ``enable-key-rotation`` command.

To specify the CMK, use the ``key-id`` parameter. This example uses an key ARN value, but you can use a key ID or key ARN in this command. Before running this command, replace the example key ARN with a valid one. ::

    aws kms disable-key-rotation \
        --key-id arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab

This command produces no output. To verify that automatic rotation is disable for the CMK, use the ``get-key-rotation-status`` command.

For more information, see `Rotating Keys <https://docs.aws.amazon.com/kms/latest/developerguide/rotate-keys.html>`__ in the *AWS Key Management Service Developer Guide*.
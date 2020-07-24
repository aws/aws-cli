**To enable automatic rotation of a customer master key (CMK)**

The following ``enable-key-rotation`` example enables automatic rotation of a customer managed customer master key (CMK). The CMK will be rotated one year (365 days) from the date that this command completes and every year thereafter. 

To specify the CMK, use the ``key-id`` parameter. This example uses a key ARN value, but you can use a key ID or key ARN in this command.

Before running this command, replace the example key ARN with a valid one. ::

    aws kms enable-key-rotation \
        --key-id arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab

This command produces no output. To verify that the CMK is enabled, use the ``get-key-rotation-status`` command.

For more information, see `Rotating Keys <https://docs.aws.amazon.com/kms/latest/developerguide/rotate-keys.html>`__ in the *AWS Key Management Service Developer Guide*.
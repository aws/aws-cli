**To determine whether a customer master key (CMK) is automatically rotated.**

The following ``get-key-rotation-status`` example determines whether a CMK is automatically rotated. You can use this command on customer managed CMKs and AWS managed CMKs. However, all AWS managed CMKs are automatically rotated every three years. 

To specify the CMK, use the ``key-id`` parameter. This example uses a key ARN value, but you can use a key ID or key ARN in this command.

Before running this command, replace the example key ARN with a valid one. ::

    aws kms get-key-rotation-status \
        --key-id 1234abcd-12ab-34cd-56ef-1234567890ab

Output::

    {
        "KeyRotationEnabled": true
    }

For more information, see `Rotating Keys <https://docs.aws.amazon.com/kms/latest/developerguide/rotate-keys.html>`__ in the *AWS Key Management Service Developer Guide*.
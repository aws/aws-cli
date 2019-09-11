**To cancel the scheduled deletion of a customer managed CMK**

The following ``cancel-key-deletion`` example cancels the scheduled deletion of a customer managed CMK and re-enables the CMK so you can use it in cryptographic operations.

The first command in the example uses the ``cancel-key-deletion`` command to cancel the scheduled deletion of the CMK. It uses the ``--key-id`` parameter to identify the CMK. This example uses a key ID value, but you can use either the key ID or the key ARN of the CMK.


To re-enable the CMK, use the ``enable-key`` command. To identify the CMK, use the ``--key-id`` parameter. This example uses a key ID value, but you can use either the key ID or the key ARN of the CMK. ::

    aws kms cancel-key-deletion \
        --key-id 1234abcd-12ab-34cd-56ef-1234567890ab

The ``cancel-key-deletion`` response returns the key ARN of the CMK whose deletion was canceled. ::

    {
        "KeyId": "arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab"
    }

When the ``cancel-key-deletion`` command succeeds, the scheduled deletion is canceled. However, the key state of the CMK is ``Disabled``, so you can't use the CMK in cryptographic operations. To restore its functionality, you must re-enable the CMK. ::

    aws kms enable-key \
        --key-id 1234abcd-12ab-34cd-56ef-1234567890ab 

The ``enable-key`` operation does not return a response. To verify that the CMK is re-enabled and there is no deletion date associated with the CMK, use the ``describe-key`` operation.

For more information, see `Scheduling and Canceling Key Deletion <https://docs.aws.amazon.com/kms/latest/developerguide/deleting-keys.html#deleting-keys-scheduling-key-deletion>`__ in the *AWS Key Management Service Developer Guide*.

**To schedule the deletion of a customer managed CMK.**

The following ``schedule-key-deletion`` example schedules the specified customer managed CMK to be deleted in 15 days. 

* The ``--key-id`` parameter identifies the CMK. This example uses a key ARN value, but you can use either the key ID or the ARN of the CMK.
* The ``--pending-window-in-days`` parameter specifies the length of the waiting period. By default, the waiting period is 30 days. This example specifies a value of 15, which tells AWS to permanently delete the CMK 15 days after the command completes. ::

    aws kms schedule-key-deletion \
        --key-id arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab \
        --pending-window-in-days 15

The response returns the key ARN and the deletion date in Unix time. To view the deletion date in local time, use the AWS KMS console. ::

    {
        "KeyId": "arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab",
        "DeletionDate": 1567382400.0
    }

For more information, see `Deleting Customer Master Keys <https://docs.aws.amazon.com/kms/latest/developerguide/deleting-keys.html>`__ in the *AWS Key Management Service Developer Guide*.

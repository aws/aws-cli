**To schedule the deletion of a customer managed CMK.**

The following ``schedule-key-deletion`` example schedules the specified customer managed CMK to be deleted in 15 days. ::

    aws kms schedule-key-deletion \
        --key-id arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab \
        --pending-window-in-days 15

Output::

    {
        "KeyId": "arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab",
        "DeletionDate": 1567382400.0
    }

For more information, see `Deleting Customer Master Keys <https://docs.aws.amazon.com/kms/latest/developerguide/deleting-keys.html>`__ in the *AWS Key Management Service Developer Guide*.

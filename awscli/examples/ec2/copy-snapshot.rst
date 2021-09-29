**Example 1: To copy a snapshot**

The following ``copy-snapshot`` example command copies the specified snapshot from the ``us-west-2`` Region to the ``us-east-1`` Region and adds a short description. ::

    aws ec2 copy-snapshot \
        --region us-east-1 \
        --source-region us-west-2 \
        --source-snapshot-id snap-066877671789bd71b \
        --description "This is my copied snapshot."

Output::

    {
        "SnapshotId": "snap-066877671789bd71b"
    }

**Example 2: To copy an unencrypted snapshot and encrypt the new snapshot**

The following ``copy-snapshot`` command copies the specified unencrypted snapshot from the ``us-west-2`` Region to the current Region and encrypts the new snapshot using the specified AWS KMS customer master key (CMK). ::

    aws ec2 copy-snapshot \
        --source-region us-west-2 \
        --source-snapshot-id snap-066877671789bd71b \
        --encrypted \
        --kms-key-id alias/my-cmk

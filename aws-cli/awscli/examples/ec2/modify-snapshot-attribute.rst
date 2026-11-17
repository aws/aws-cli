**Example 1: To modify a snapshot attribute**

The following ``modify-snapshot-attribute`` example updates the ``createVolumePermission`` attribute for the specified snapshot, removing volume permissions for the specified user. ::

    aws ec2 modify-snapshot-attribute \
        --snapshot-id snap-1234567890abcdef0 \
        --attribute createVolumePermission \
        --operation-type remove \
        --user-ids 123456789012

This command produces no output.

For more information, see `Share an Amazon EBS snapshot with other AWS accounts <https://docs.aws.amazon.com/ebs/latest/userguide/ebs-modifying-snapshot-permissions.html>`__ in the *Amazon EBS User Guide*.

**Example 2: To make a snapshot public**

The following ``modify-snapshot-attribute`` example makes the specified snapshot public. ::

    aws ec2 modify-snapshot-attribute \
        --snapshot-id snap-1234567890abcdef0 \
        --attribute createVolumePermission \
        --operation-type add \
        --group-names all

This command produces no output.

For more information, see `Share an Amazon EBS snapshot with other AWS accounts <https://docs.aws.amazon.com/ebs/latest/userguide/ebs-modifying-snapshot-permissions.html>`__ in the *Amazon EBS User Guide*.

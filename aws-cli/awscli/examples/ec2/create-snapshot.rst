**Example 1: To create a snapshot**

The following ``create-snapshot`` example creates a snapshot of the volume with a volume ID of ``vol-1234567890abcdef0`` and a short description to identify the snapshot. ::

    aws ec2 create-snapshot \
        --volume-id vol-1234567890abcdef0 \
        --description "This is my root volume snapshot"

Output::

    {
        "Description": "This is my root volume snapshot",
        "Tags": [],
        "Encrypted": false,
        "VolumeId": "vol-1234567890abcdef0",
        "State": "pending",
        "VolumeSize": 8,
        "StartTime": "2018-02-28T21:06:01.000Z",
        "Progress": "",
        "OwnerId": "123456789012",
        "SnapshotId": "snap-0abcdef1234567890"
    }

For more information, see `Create Amazon EBS snapshots <https://docs.aws.amazon.com/ebs/latest/userguide/ebs-creating-snapshot.html>`__ in the *Amazon EBS User Guide*.

**Example 2: To create a snapshot with tags**

The following ``create-snapshot`` example creates a snapshot and applies two tags: purpose=prod and costcenter=123. ::

    aws ec2 create-snapshot \
        --volume-id vol-1234567890abcdef0 \
        --description 'Prod backup' \
        --tag-specifications 'ResourceType=snapshot,Tags=[{Key=purpose,Value=prod},{Key=costcenter,Value=123}]'

Output::

    {
        "Description": "Prod backup",
        "Tags": [
            {
                "Value": "prod",
                "Key": "purpose"
            },
            {
                "Value": "123",
                "Key": "costcenter"
            }
        ],
        "Encrypted": false,
        "VolumeId": "vol-1234567890abcdef0",
        "State": "pending",
        "VolumeSize": 8,
        "StartTime": "2018-02-28T21:06:06.000Z",
        "Progress": "",
        "OwnerId": "123456789012",
        "SnapshotId": "snap-09ed24a70bc19bbe4"
    }

For more information, see `Create Amazon EBS snapshots <https://docs.aws.amazon.com/ebs/latest/userguide/ebs-creating-snapshot.html>`__ in the *Amazon EBS User Guide*.

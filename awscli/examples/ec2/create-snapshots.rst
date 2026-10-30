**Example 1: To create a multi-volume snapshot**

The following ``create-snapshots`` example creates snapshots of all volumes attached to the specified instance. ::

    aws ec2 create-snapshots \
        --instance-specification InstanceId=i-1234567890abcdef0 \
        --description "This is snapshot of a volume from my-instance"

Output::

    {
        "Snapshots": [
            {
                "Description": "This is snapshot of a volume from my-instance",
                "Tags": [],
                "Encrypted": false,
                "VolumeId": "vol-0a01d2d5a34697479",
                "State": "pending",
                "VolumeSize": 16,
                "StartTime": "2019-08-05T16:58:19.000Z",
                "Progress": "",
                "OwnerId": "123456789012",
                "SnapshotId": "snap-07f30e3909aa0045e"
            },
            {
                "Description": "This is snapshot of a volume from my-instance",
                "Tags": [],
                "Encrypted": false,
                "VolumeId": "vol-02d0d4947008cb1a2",
                "State": "pending",
                "VolumeSize": 20,
                "StartTime": "2019-08-05T16:58:19.000Z",
                "Progress": "",
                "OwnerId": "123456789012",
                "SnapshotId": "snap-0ec20b602264aad48"
            }
        ]
    }

For more information, see `Create Amazon EBS snapshots <https://docs.aws.amazon.com/ebs/latest/userguide/ebs-creating-snapshot.html>`__ in the *Amazon EBS User Guide*.

**Example 2: To create a multi-volume snapshot with tags from the source volume**

The following ``create-snapshots`` example creates snapshots of all volumes attached to the specified instance and copies the tags from each volume to its corresponding snapshot. ::

    aws ec2 create-snapshots \
        --instance-specification InstanceId=i-1234567890abcdef0 \
        --copy-tags-from-source volume \
        --description "This is snapshot of a volume from my-instance"

Output::

    {
        "Snapshots": [
            {
                "Description": "This is snapshot of a volume from my-instance",
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": "my-volume"
                    }
                ],
                "Encrypted": false,
                "VolumeId": "vol-02d0d4947008cb1a2",
                "State": "pending",
                "VolumeSize": 20,
                "StartTime": "2019-08-05T16:53:04.000Z",
                "Progress": "",
                "OwnerId": "123456789012",
                "SnapshotId": "snap-053bfaeb821a458dd"
            }
        ]
    }

For more information, see `Create Amazon EBS snapshots <https://docs.aws.amazon.com/ebs/latest/userguide/ebs-creating-snapshot.html>`__ in the *Amazon EBS User Guide*.

**Example 3: To create a multi-volume snapshot not including the root volume**

The following ``create-snapshots`` example creates a snapshot of all volumes attached to the specified instance except for the root volume. ::

    aws ec2 create-snapshots \
        --instance-specification InstanceId=i-1234567890abcdef0,ExcludeBootVolume=true

Output::

    {
        "Snapshots": [
            {
                "Description": "",
                "Tags": [],
                "Encrypted": false,
                "VolumeId": "vol-02d0d4947008cb1a2",
                "State": "pending",
                "VolumeSize": 20,
                "StartTime": "2019-08-05T17:02:41.000Z",
                "Progress": "",
                "OwnerId": "123456789012",
                "SnapshotId": "snap-0a1b2c3d4e5f67890"
            }
        ]
    }

For more information, see `Create Amazon EBS snapshots <https://docs.aws.amazon.com/ebs/latest/userguide/ebs-creating-snapshot.html>`__ in the *Amazon EBS User Guide*.

**Example 4: To create a multi-volume snapshot and add tags**

The following ``create-snapshots`` example creates snapshots of all volumes attached to the specified instance and adds two tags to each snapshot. ::

    aws ec2 create-snapshots \
        --instance-specification InstanceId=i-1234567890abcdef0 \
        --tag-specifications 'ResourceType=snapshot,Tags=[{Key=Name,Value=backup},{Key=costcenter,Value=123}]'

Output::

    {
        "Snapshots": [
            {
                "Description": "",
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": "backup"
                    },
                    {
                        "Key": "costcenter",
                        "Value": "123"
                    }
                ],
                "Encrypted": false,
                "VolumeId": "vol-0a01d2d5a34697479",
                "State": "pending",
                "VolumeSize": 16,
                "StartTime": "2019-08-05T17:05:12.000Z",
                "Progress": "",
                "OwnerId": "123456789012",
                "SnapshotId": "snap-01234567890abcdef"
            },
            {
                "Description": "",
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": "backup"
                    },
                    {
                        "Key": "costcenter",
                        "Value": "123"
                    }
                ],
                "Encrypted": false,
                "VolumeId": "vol-02d0d4947008cb1a2",
                "State": "pending",
                "VolumeSize": 20,
                "StartTime": "2019-08-05T17:05:12.000Z",
                "Progress": "",
                "OwnerId": "123456789012",
                "SnapshotId": "snap-0fedcba9876543210"
            }
        ]
    }

For more information, see `Create Amazon EBS snapshots <https://docs.aws.amazon.com/ebs/latest/userguide/ebs-creating-snapshot.html>`__ in the *Amazon EBS User Guide*.

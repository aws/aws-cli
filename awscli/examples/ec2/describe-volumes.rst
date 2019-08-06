**Example 1: To describe all volumes**

The following ``describe-volumes`` example describes all of your volumes in the current Region. ::

  aws ec2 describe-volumes

Output::

    {
        "Volumes": [
            {
                "AvailabilityZone": "us-east-1a",
                "Attachments": [
                    {
                        "AttachTime": "2013-12-18T22:35:00.000Z",
                        "InstanceId": "i-1234567890abcdef0",
                        "VolumeId": "vol-049df61146c4d7901",
                        "State": "attached",
                        "DeleteOnTermination": true,
                        "Device": "/dev/sda1"
                    }
                ],
                "Encrypted": false,
                "VolumeType": "gp2",
                "VolumeId": "vol-049df61146c4d7901",
                "State": "in-use",
                "SnapshotId": "snap-1234567890abcdef0",
                "CreateTime": "2013-12-18T22:35:00.084Z",
                "Size": 8
            },
            {
                "AvailabilityZone": "us-east-1a",
                "Attachments": [],
                "Encrypted": false,
                "VolumeType": "gp2",
                "VolumeId": "vol-1234567890abcdef0",
                "State": "available",
                "Iops": 1000,
                "SnapshotId": null,
                "CreateTime": "2014-02-27T00:02:41.791Z",
                "Size": 100
            }
        ]
    }

**Example 2: To describe volumes that are attached to a specific instance**

The following ``describe-volumes`` example describes all volumes that are both attached to the specified instance and set to delete when the instance terminates. ::

    aws ec2 describe-volumes \
        --region us-east-1 \
        --filters Name=attachment.instance-id,Values=i-1234567890abcdef0 Name=attachment.delete-on-termination,Values=true

Output::

    {
        "Volumes": [
            {
                "AvailabilityZone": "us-east-1a",
                "Attachments": [
                    {
                        "AttachTime": "2013-12-18T22:35:00.000Z",
                        "InstanceId": "i-1234567890abcdef0",
                        "VolumeId": "vol-049df61146c4d7901",
                        "State": "attached",
                        "DeleteOnTermination": true,
                        "Device": "/dev/sda1"
                    }
                ],
                "Encrypted": false,
                "VolumeType": "gp2",
                "VolumeId": "vol-049df61146c4d7901",
                "State": "in-use",
                "SnapshotId": "snap-1234567890abcdef0",
                "CreateTime": "2013-12-18T22:35:00.084Z",
                "Size": 8
            }
        ]
    }

**Example 3: To describe available volumes in a specific Availability Zone**

The following ``describe-volumes`` example describes all volumes that have a status of ``available`` and are in the specified Availability Zone. ::

    aws ec2 describe-volumes \
        --filters Name=status,Values=available Name=availability-zone,Values=us-east-1a

Output::

    {
        "Volumes": [
            {
                "AvailabilityZone": "us-east-1a",
                "Attachments": [],
                "Encrypted": false,
                "VolumeType": "gp2",
                "VolumeId": "vol-1234567890abcdef0",
                "State": "available",
                "Iops": 1000,
                "SnapshotId": null,
                "CreateTime": "2014-02-27T00:02:41.791Z",
                "Size": 100
            }
        ]
    }

**Example 4: To describe tagged volumes and filter the output**

The following ``describe-volumes`` example describes all volumes that have the tag key ``Name`` and a value that begins with ``Test``. The output is then filtered with a query that displays only the tags and IDs of the volumes. ::

    aws ec2 describe-volumes \
        --filters Name=tag:Name,Values=Test* \
        --query "Volumes[*].{ID:VolumeId,Tag:Tags}"

Output::

    [
        {
           "Tag": [
               {
                   "Value": "Test2", 
                   "Key": "Name"
               }
           ], 
           "ID": "vol-1234567890abcdef0"
       }, 
       {
           "Tag": [
               {
                   "Value": "Test1", 
                   "Key": "Name"
               }
           ], 
           "ID": "vol-049df61146c4d7901"
        }
    ]

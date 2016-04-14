**To describe all volumes**

This example command describes all of your volumes in the default region.

Command::

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
                       "VolumeId": "vol-21083656",
                       "State": "attached",
                       "DeleteOnTermination": true,
                       "Device": "/dev/sda1"
                   }
               ],
               "VolumeType": "standard",
               "VolumeId": "vol-21083656",
               "State": "in-use",
               "SnapshotId": "snap-b4ef17a9",
               "CreateTime": "2013-12-18T22:35:00.084Z",
               "Size": 8
           },
           {
               "AvailabilityZone": "us-east-1a",
               "Attachments": [],
               "VolumeType": "io1",
               "VolumeId": "vol-2725bc51",
               "State": "available",
               "Iops": 1000,
               "SnapshotId": null,
               "CreateTime": "2014-02-27T00:02:41.791Z",
               "Size": 100
           }
       ]
   }

**To describe volumes that are attached to a specific instance**

This example command describes all volumes that are both attached to the instance with the ID i-1234567890abcdef0 and set to delete when the instance terminates.

Command::

  aws ec2 describe-volumes --region us-east-1 --filters Name=attachment.instance-id,Values=i-1234567890abcdef0 Name=attachment.delete-on-termination,Values=true

Output::

   {
       "Volumes": [
           {
               "AvailabilityZone": "us-east-1a",
               "Attachments": [
                   {
                       "AttachTime": "2013-12-18T22:35:00.000Z",
                       "InstanceId": "i-1234567890abcdef0",
                       "VolumeId": "vol-21083656",
                       "State": "attached",
                       "DeleteOnTermination": true,
                       "Device": "/dev/sda1"
                   }
               ],
               "VolumeType": "standard",
               "VolumeId": "vol-21083656",
               "State": "in-use",
               "SnapshotId": "snap-b4ef17a9",
               "CreateTime": "2013-12-18T22:35:00.084Z",
               "Size": 8
           }
       ]
   }
 
**To describe tagged volumes and filter the output**

This example command describes all volumes that have the tag key ``Name`` and a value that begins with ``Test``. The output is filtered to display only the tags and IDs of the volumes. 

Command::

  aws ec2 describe-volumes --filters Name=tag-key,Values="Name" Name=tag-value,Values="Test*" --query 'Volumes[*].{ID:VolumeId,Tag:Tags}'

Output::

   [
     {
        "Tag": [
            {
                "Value": "Test2", 
                "Key": "Name"
            }
        ], 
        "ID": "vol-9de9e9d9"
    }, 
    {
        "Tag": [
            {
                "Value": "Test1", 
                "Key": "Name"
            }
        ], 
        "ID": "vol-b2242df9"
     }
   ]


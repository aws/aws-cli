**To view information on all volumes**

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
                       "InstanceId": "i-abe041d4",
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

**To view filtered information on all volumes**

This example command describes all volumes that are both attached to the instance with the ID i-abe041d4 and set to delete when the instance terminates.

Command::

  aws ec2 describe-volumes --region us-east-1 --filter Name=attachment.instance-id,Values=i-abe041d4 --filter Name=attachment.delete-on-termination,Values=true

Output::

   {
       "Volumes": [
           {
               "AvailabilityZone": "us-east-1a",
               "Attachments": [
                   {
                       "AttachTime": "2013-12-18T22:35:00.000Z",
                       "InstanceId": "i-abe041d4",
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
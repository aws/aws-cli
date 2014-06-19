**To create a new volume**

This example command creates an 80 GiB General Purpose (SSD) volume in the Availability Zone ``us-east-1a``.

Command::

  aws ec2 create-volume --size 80 --region us-east-1 --availability-zone us-east-1a --volume-type gp2

Output::

   {
       "AvailabilityZone": "us-east-1a",
       "Attachments": [],
       "Tags": [],
       "VolumeType": "gp2",
       "VolumeId": "vol-1234abcd",
       "State": "creating",
       "SnapshotId": null,
       "CreateTime": "YYYY-MM-DDTHH:MM:SS.000Z",
       "Size": 80
   }

**To create a new Provisioned IOPS (SSD) volume from a snapshot**

This example command creates a new Provisioned IOPS (SSD) volume with 1000 provisioned IOPS from a snapshot in the Availability Zone ``us-east-1a``.

Command::

  aws ec2 create-volume --region us-east-1 --availability-zone us-east-1a --snapshot-id snap-abcd1234 --volume-type io1 --iops 1000

Output::

   {
       "AvailabilityZone": "us-east-1a",
       "Attachments": [],
       "Tags": [],
       "VolumeType": "io1",
       "VolumeId": "vol-1234abcd",
       "State": "creating",
       "Iops": 1000,
       "SnapshotId": "snap-abcd1234",
       "CreateTime": "YYYY-MM-DDTHH:MM:SS.000Z",
       "Size": 500
   }

**To attach a volume to an instance**

This example command attaches a volume (``vol-1234abcd``) to an instance (``i-01474ef662b89480``) as ``/dev/sdf``.

Command::

  aws ec2 attach-volume --volume-id vol-1234abcd --instance-id i-01474ef662b89480 --device /dev/sdf

Output::

   {
       "AttachTime": "YYYY-MM-DDTHH:MM:SS.000Z",
       "InstanceId": "i-01474ef662b89480",
       "VolumeId": "vol-1234abcd",
       "State": "attaching",
       "Device": "/dev/sdf"
   }

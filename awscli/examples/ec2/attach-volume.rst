**To attach a volume to an instance**

This example command attaches a volume (``vol-1234abcd``) to an instance (``i-abcd1234``) as ``/dev/sdf``.

Command::

  aws ec2 attach-volume --volume-id vol-1234abcd --instance-id i-abcd1234 --device /dev/sdf

Output::

   {
       "AttachTime": "YYYY-MM-DDTHH:MM:SS.000Z",
       "InstanceId": "i-abcd1234",
       "VolumeId": "vol-1234abcd",
       "State": "attaching",
       "Device": "/dev/sdf"
   }

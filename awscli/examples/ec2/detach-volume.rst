**To detach a volume from an instance**

This example command detaches the volume (``vol-1234abcd``) from the instance it is attached to.

Command::

  aws ec2 detach-volume --volume-id vol-1234abcd

Output::

   {
       "AttachTime": "2014-02-27T19:23:06.000Z",
       "InstanceId": "i-0751440e",
       "VolumeId": "vol-1234abcd",
       "State": "detaching",
       "Device": "/dev/sdb"
   }
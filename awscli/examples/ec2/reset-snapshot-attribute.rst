**To reset a snapshot attribute**

This example resets the create volume permissions for snapshot ``snap-1a2b3c4d``. If the command succeeds, no output is returned.

Command::

  aws ec2 reset-snapshot-attribute --snapshot-id snap-1a2b3c4d --attribute createVolumePermission


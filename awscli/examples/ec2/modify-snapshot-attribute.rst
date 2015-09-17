**To modify a snapshot attribute**

This example modifies snapshot ``snap-1a2b3c4d`` to remove the create volume permission for a user with the account ID ``123456789012``. If the command succeeds, no output is returned.

Command::

  aws ec2 modify-snapshot-attribute --snapshot-id snap-1a2b3c4d --attribute createVolumePermission --operation-type remove --user-ids 123456789012

**To make a snapshot public**

This example makes the snapshot ``snap-1a2b3c4d`` public.

Command::

  aws ec2 modify-snapshot-attribute --snapshot-id snap-1a2b3c4d --attribute createVolumePermission --operation-type add --group-names all
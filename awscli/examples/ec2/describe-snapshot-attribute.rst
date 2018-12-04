**To describe snapshot attributes**

This example command describes the ``createVolumePermission`` attribute on a snapshot with the snapshot ID of ``snap-066877671789bd71b``.

Command::

  aws ec2 describe-snapshot-attribute --snapshot-id snap-066877671789bd71b --attribute createVolumePermission

Output::

   {
       "SnapshotId": "snap-066877671789bd71b",
       "CreateVolumePermissions": []
   }
**To describe snapshot attributes**

This example command describes the ``createVolumePermission`` and ``productCodes`` attributes on a snapshot with the snapshot ID of ``snap-066877671789bd71b``.

Command::

  aws ec2 describe-snapshot-attribute --snapshot-id snap-066877671789bd71b --attribute createVolumePermission --attribute productCodes

Output::

   {
       "SnapshotId": "snap-066877671789bd71b",
       "CreateVolumePermissions": [],
       "ProductCodes": []
   }
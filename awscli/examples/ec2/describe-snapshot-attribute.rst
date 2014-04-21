**To describe snapshot attributes**

This example command describes the ``createVolumePermission`` and ``productCodes`` attributes on a snapshot with the snapshot ID of ``snap-1234abcd``.

Command::

  aws ec2 describe-snapshot-attribute --snapshot-id snap-1234abcd --attribute createVolumePermission --attribute productCodes

Output::

   {
       "SnapshotId": "snap-b52c0044",
       "CreateVolumePermissions": [],
       "ProductCodes": []
   }
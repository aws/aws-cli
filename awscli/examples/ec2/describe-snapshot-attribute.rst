**To describe the snapshot attributes for a snapshot**

The following ``describe-snapshot`` example describes the ``createVolumePermission`` attribute for the specified snapshot. ::

    aws ec2 describe-snapshot-attribute \
        --snapshot-id snap-066877671789bd71b \
        --attribute createVolumePermission

The output indicates that the specified user has volume permissions. ::

    {
        "SnapshotId": "snap-066877671789bd71b",
        "CreateVolumePermissions": [
            {
                "UserId": "123456789012"
            }
        ]
    }
   
Output similar to the following indicates that there are no volume permissions. ::

    {
        "SnapshotId": "snap-066877671789bd71b",
        "CreateVolumePermissions": []
    }

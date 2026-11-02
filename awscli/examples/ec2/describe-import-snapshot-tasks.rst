**To monitor an import snapshot task**

The following ``describe-import-snapshot-tasks`` example checks the status of the specified import snapshot task. ::

    aws ec2 describe-import-snapshot-tasks \
        --import-task-ids import-snap-1234567890abcdef0

The following example output is for an import snapshot task that is in progress.

Output::

    {
        "ImportSnapshotTasks": [
            {
                "Description": "My server VMDK",
                "ImportTaskId": "import-snap-1234567890abcdef0",
                "SnapshotTaskDetail": {
                    "Description": "My server VMDK",
                    "DiskImageSize": 705638400.0,
                    "Format": "VMDK",
                    "Progress": "42",
                    "Status": "active",
                    "StatusMessage": "downloading/converting",
                    "UserBucket": {
                        "S3Bucket": "my-import-bucket",
                        "S3Key": "vms/my-server-vm.vmdk"
                    }
                }
            }
        ]
    }

The following example output is for an import snapshot task that is completed. The ID of the resulting snapshot is provided by ``SnapshotId``.

Output::

    {
        "ImportSnapshotTasks": [
            {
                "Description": "My server VMDK",
                "ImportTaskId": "import-snap-1234567890abcdef0",
                "SnapshotTaskDetail": {
                    "Description": "My server VMDK",
                    "DiskImageSize": 705638400.0,
                    "Format": "VMDK",
                    "SnapshotId": "snap-1234567890abcdef0",
                    "Status": "completed",
                    "UserBucket": {
                        "S3Bucket": "my-import-bucket",
                        "S3Key": "vms/my-server-vm.vmdk"
                    }
                }
            }
        ]
    }

For more information, see `Import a disk as an EBS snapshot using VM Import/Export <https://docs.aws.amazon.com/vm-import/latest/userguide/vmimport-import-snapshot.html>`__ in the *VM Import/Export User Guide*.

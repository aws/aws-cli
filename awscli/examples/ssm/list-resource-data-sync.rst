**To list your resource data sync configurations**

The following ``list-resource-data-sync`` example retrieves information about your resource data sync configurations. ::

    aws ssm list-resource-data-sync

Output::

    {
        "ResourceDataSyncItems": [
            {
                "SyncName": "MyResourceDataSync",
                "S3Destination": {
                    "BucketName": "amzn-s3-demo-bucket",
                    "SyncFormat": "JsonSerDe",
                    "Region": "us-west-2"
                },
                "LastSyncTime": 1550261472.003,
                "LastSuccessfulSyncTime": 1550261472.003,
                "LastStatus": "Successful",
                "SyncCreatedTime": 1543235736.72,
                "LastSyncStatusMessage": "The sync was successfully completed"
            }
        ]
    }

For more information, see `Creating a resource data sync for Inventory <https://docs.aws.amazon.com/systems-manager/latest/userguide/inventory-create-resource-data-sync.html>`__ in the *AWS Systems Manager User Guide*.

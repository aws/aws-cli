**To list your resource data sync configurations**

This example retrieves information about your resource data sync configurations.

Command::

  aws ssm list-resource-data-sync --sync-name "ssm-resource-data-sync"

Output::

  {
    "ResourceDataSyncItems": [
        {
            "SyncName": "ssm-resource-data-sync",
            "S3Destination": {
                "BucketName": "ssm-resource-data-sync",
                "SyncFormat": "JsonSerDe",
                "Region": "us-east-1"
            },
            "LastSyncTime": 1550261472.003,
            "LastSuccessfulSyncTime": 1550261472.003,
            "LastStatus": "Successful",
            "SyncCreatedTime": 1543235736.72,
            "LastSyncStatusMessage": "The sync was successfully completed"
        }
    ]
  }

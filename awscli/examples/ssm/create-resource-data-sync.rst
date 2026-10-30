**To create a resource data sync**

The following ``create-resource-data-sync`` example creates a resource data sync. There is no output if the command succeeds. ::

    aws ssm create-resource-data-sync --sync-name "ssm-resource-data-sync" --s3-destination "BucketName=ssm-bucket,Prefix=inventory,SyncFormat=JsonSerDe,Region=us-east-1"

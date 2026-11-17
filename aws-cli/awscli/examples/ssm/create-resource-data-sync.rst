**To create a resource data sync**

The following ``create-resource-data-sync`` example creates a resource data sync. ::

    aws ssm create-resource-data-sync \
        --sync-name "ssm-resource-data-sync" \
        --s3-destination "BucketName=ssm-bucket,Prefix=inventory,SyncFormat=JsonSerDe,Region=us-west-2"

This command produces no output.

For more information, see `Creating a resource data sync for Inventory <https://docs.aws.amazon.com/systems-manager/latest/userguide/inventory-create-resource-data-sync.html>`__ in the *AWS Systems Manager User Guide*.

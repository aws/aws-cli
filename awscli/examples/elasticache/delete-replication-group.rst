**To delete a replication group**

The following ``delete-replication-group`` example deletes the specified replication group. By default, this operation deletes the entire replication group, including the primary or primaries and all of the read replicas. If the replication group has only one primary, you can optionally delete only the read replicas, while keeping the primary by setting ``--retain-primary-cluster``.

When you get a successful response from this operation, Amazon ElastiCache immediately begins deleting the selected resources; you can't cancel or revert this operation. This operation is valid for Redis only.

    aws elasticache delete-replication-group \
        --replication-group-id "mygroup" 

Output::

   {
        "ReplicationGroup": {
            "ReplicationGroupId": "mygroup",
            "Description": "my group",
            "Status": "deleting",
            "PendingModifiedValues": {},
            "AutomaticFailover": "disabled",
            "SnapshotRetentionLimit": 0,
            "SnapshotWindow": "06:00-07:00",
            "TransitEncryptionEnabled": false,
            "AtRestEncryptionEnabled": false
        }
    }

For more information, see `Deleting a Replication Group <https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Replication.DeletingRepGroup.html>`__ in the *Elasticache User Guide*.

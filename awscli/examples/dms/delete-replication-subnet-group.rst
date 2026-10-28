**To delete a subnet group**

The following ``delete-replication-subnet-group`` example deletes a subnet group. This command produces no output. ::

    aws dms delete-replication-subnet-group \
        --replication-subnet-group-identifier my-subnet-group

For more information, see `Setting Up a Network for a Replication Instance <https://docs.aws.amazon.com/dms/latest/userguide/CHAP_ReplicationInstance.VPC.html>`__ in the *AWS Database Migration Service User Guide*.

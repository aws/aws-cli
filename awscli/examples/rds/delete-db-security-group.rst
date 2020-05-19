**To delete a DB security group**

The following ``delete-db-security-group`` example deletes the DB security group named ``mysecgroup``. ::

    aws rds delete-db-security-group \
        --db-security-group-name mysecgroup

This command produces no output.

For more information, see `Deleting DB VPC Security Groups <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.RDSSecurityGroups.html#Overview.RDSSecurityGroups.DeleteDBVPCGroups>`__ in the *Amazon RDS User Guide*.

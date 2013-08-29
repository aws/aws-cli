**To create an Amazon RDS DB security group**

The following ``create-db-security-group`` command creates a new Amazon RDS DB security group::

    aws rds create-db-security-group --db-security-group-name mysecgroup --db-security-group-description "My Test Security Group"

In the example, the new DB security group is named ``mysecgroup`` and has a description.

This command output a JSON block that contains information about the DB security group.

For more information, see `Create an Amazon RDS DB Security Group`_ in the *AWS Command Line Interface User Guide*.

.. _`Create an Amazon RDS DB Security Group`: http://docs.aws.amazon.com/cli/latest/userguide/cli-rds-create-secgroup.html


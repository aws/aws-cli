**To update a registered Amazon RDS DB instance**

The following example updates an Amazon RDS instance's master password value.
Note that this command does not change the RDS instance's master password, just the password that
you provide to AWS OpsWorks.
If this password does not match the RDS instance's password,
your application will not be able to connect to the database. ::

  aws opsworks --region us-east-1 update-rds-db-instance --db-password 123456789

**Note**: AWS OpsWorks CLI commands should set the region to ``us-east-1`` regardless of the stack's location.

*Output*: None.

**More Information**

For more information, see `Registering Amazon RDS Instances with a Stack`_ in the *AWS OpsWorks User Guide*.

.. _`Registering Amazon RDS Instances with a Stack`: http://docs.aws.amazon.com/opsworks/latest/userguide/resources-reg.html#resources-reg-rds


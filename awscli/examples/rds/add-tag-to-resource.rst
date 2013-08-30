**To add a tag to an Amazon RDS resource**

The following ``add-tags-to-resource`` command adds a tag to an Amazon RDS resource. In the example, a DB instance is
identified by the instance's ARN, arn:aws:rds:us-west-2:001234567890:db:mysql-db1. The tag that is added to the DB
instance has a key of ``project`` and a value of ``salix``::

    aws rds add-tags-to-resource --resource-name arn:aws:rds:us-west-2:001234567890:db:mysql-db1 --tags account=sg01,project=salix

This command outputs a JSON block that acknowledges the change to the RDS resource.

For more information, see `Tagging an Amazon RDS DB Instance`_ in the *AWS Command Line Interface User Guide*.

.. _`Tagging an Amazon RDS DB Instance`: http://docs.aws.amazon.com/cli/latest/userguide/cli-rds-add-tags.html


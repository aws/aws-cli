**To create an Amazon RDS DB instance**

The following ``create-db-instance`` command launches a new Amazon RDS DB instance::

    aws rds create-db-instance sg-CLI-Test --allocated-storage 20 --db-instance-class db.m1.small --engine mysql --master-username myawsuser --master-user-password myawsuser

In the preceding example, the DB instance is created with 20 Gb of standard storage and has a DB engine class of db.m1.small.
The master username and master password are provided.

This command outputs a JSON block that indicates that the DB instance was created.

Output::

    DBINSTANCE  sg-cli-test  db.m1.small  mysql  20  myawsuser  creating  1  ****  n
      5.5.31  general-public-license  y
          SECGROUP  default  active
          PARAMGRP  default.mysql5.5  in-sync

          OPTIONGROUP  default:mysql-5-5  in-sync

For more information, see `Create an Amazon RDS DB Instance`_ in the *AWS Command Line Interface User Guide*.

.. _`Create an Amazon RDS DB Instance`: http://docs.aws.amazon.com/cli/latest/userguide/cli-rds-create-instance.html


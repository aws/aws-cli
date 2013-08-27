**To launch an Amazon EC2 instance**

The following ``create-option-group`` command creates a new Amazon RDS option group.
In the example, the option group is created for Oracle Enterprise Edition version 11.2
and is named MyOptionGroup and includes a description.
::

    aws rds create-option-group MyOptionGroup -e oracle-ee -v 11.2 -d "Oracle Database Manager Database Control"

This command output a JSON block that contains information on the option group.

For more information, see `Create an Amazon RDS Option Group`_ in the *AWS Command Line Interface User Guide*.

.. _Create an Amazon RDS Option Group: http://docs.aws.amazon.com/cli/latest/userguide/cli-rds-create-option-group.html


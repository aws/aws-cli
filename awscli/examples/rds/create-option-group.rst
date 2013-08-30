**To Create an Amazon RDS option group**

The following ``create-option-group`` command creates a new Amazon RDS option group::

   aws rds create-option-group --option-group-name MyOptionGroup --engine-name oracle-ee --major-engine-version 11.2 --option-group-description "Oracle Database Manager Database Control" 

In the example, the option group is created for Oracle Enterprise Edition version *11.2*, is named *MyOptionGroup* and
includes a description.

This command output a JSON block that contains information on the option group.

For more information, see `Create an Amazon RDS Option Group`_ in the *AWS Command Line Interface User Guide*.

.. _`Create an Amazon RDS Option Group`: http://docs.aws.amazon.com/cli/latest/userguide/cli-rds-create-option-group.html


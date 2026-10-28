**Example 1: To delete a security group (EC2-Classic)**

The following ``delete-security-group`` example deletes the security group named ``MySecurityGroup``. ::

    aws ec2 delete-security-group \
        --group-name MySecurityGroup

Output::

    {
        "Return": true,
        "GroupId": "sg-1a2b3c4d"
    }

**Example 2: To delete a security group (EC2-VPC)**

The following ``delete-security-group`` example deletes the security group with the ID ``sg-903004f8``. Note that you can't reference a security group for EC2-VPC by name. ::

    aws ec2 delete-security-group \
        --group-id sg-903004f8

Output::

    {
        "Return": true,
        "GroupId": "sg-903004f8"
    }

For more information, see `Using Security Groups`_ in the *AWS Command Line Interface User Guide*.

.. _`Using Security Groups`: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-sg.html

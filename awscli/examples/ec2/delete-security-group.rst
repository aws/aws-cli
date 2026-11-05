**Example 1: To delete a security group (EC2-Classic)**

The following ``delete-security-group`` example deletes the security group named ``MySecurityGroup``. ::

    aws ec2 delete-security-group \
        --group-name MySecurityGroup

Output::

    {
        "Return": true,
        "GroupId": "sg-1a2b3c4d"
    }

For more information, see `Delete an Amazon EC2 security group <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/deleting-security-group.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To delete a security group (EC2-VPC)**

The following ``delete-security-group`` example deletes the security group with the ID ``sg-903004f8``. Note that you can't reference a security group for EC2-VPC by name. ::

    aws ec2 delete-security-group \
        --group-id sg-903004f8

Output::

    {
        "Return": true,
        "GroupId": "sg-903004f8"
    }

For more information, see `Delete an Amazon EC2 security group <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/deleting-security-group.html>`__ in the *Amazon EC2 User Guide* and `Creating, configuring, and deleting Amazon EC2 security groups in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-services-ec2-sg.html>`__ in the *AWS CLI User Guide*.

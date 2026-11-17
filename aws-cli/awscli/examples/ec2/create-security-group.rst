**Example 1: To create a security group for EC2-Classic**

The following ``create-security-group`` example creates a security group named ``MySecurityGroup``. ::

    aws ec2 create-security-group \
        --group-name MySecurityGroup \
        --description "My security group"

Output::

    {
        "GroupId": "sg-903004f8"
    }

For more information, see `Amazon EC2 security groups for your EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security-groups.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To create a security group for EC2-VPC**

The following ``create-security-group`` example creates a security group named ``MySecurityGroup`` for the specified VPC. ::

    aws ec2 create-security-group \
        --group-name MySecurityGroup \
        --description "My security group" \
        --vpc-id vpc-1a2b3c4d

Output::

    {
        "GroupId": "sg-903004f8"
    }

For more information, see `Creating, configuring, and deleting Amazon EC2 security groups in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-services-ec2-sg.html>`__ in the *AWS Command Line Interface User Guide*.

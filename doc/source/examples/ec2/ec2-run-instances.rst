**To launch an Amazon EC2 instance**

The following ``run-instances`` command launches a single Amazon EC2 instance using
AMI ami-554ac83c, a Microsoft Windows Server 2012 image. The instance type is
t1.micro. The key pair and security groups are named MyKeyPair and
MySecurityGroup, and are assumed to have been created previously.
::

    aws ec2 run-instances --image-id ami-554ac83c count 1--key-name MyKeyPair --security-groups MySecurityGroup

This command output a JSON block that contains descriptive information about the instance.

If you launch an instance that is not within the Free Usage Tier, you are
billed after you launch the instance and charged for the time that the
instance is running, even if it remains idle.

For more information, see `Launch an Amazon EC2 Instance`_ in the *AWS Command Line Interface User Guide*.

.. _Launch an Amazon EC2 Instance: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-launch.html


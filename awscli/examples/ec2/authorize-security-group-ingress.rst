**To configure a security group to allow ingress**

The following example uses the ``authorize-security-group-ingress`` command to enable inbound traffic on TCP port 22 (SSH)::

    aws ec2 authorize-security-group-ingress --group-name MySecurityGroup --ip-protocol tcp --from-port 22 --to-port 22 --cidr-ip 203.0.113.0/24

For more information, see `Using Security Groups`_ in the *AWS Command Line Interface User Guide*.

.. _Using Security Groups: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-sg.html


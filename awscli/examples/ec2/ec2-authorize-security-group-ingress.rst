**To configure a security group to allow ingress**

The following example uses the ``authorize-security-group-ingress`` command to enable ingress on TCP port 22 (SSH)::

    aws ec2 authorize-security-group-ingress --group-name MySecurityGroup --ip-protocol tcp --from-port 22 --to-port 22 --cidr-ip 0.0.0.0/0

Output::    

  {
      "return": "true",
      "requestId": "c24a1c93-150b-4a0a-b56b-b149c0e660d2"
  }

For more information, see `Amazon EC2 Security Groups`_ in the *AWS Command Line Interface User Guide*.

.. _Amazon EC2 Security Groups: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-sg.html


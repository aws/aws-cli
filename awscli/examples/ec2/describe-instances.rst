**To describe an Amazon EC2 instance**

Command::

  aws ec2 describe-instances --instance-ids i-5203422c

**To describe all instances with the instance type m1.small**

Command::

  aws ec2 describe-instances --filters "Name=instance-type,Values=m1.small"

**To describe all instances with an Owner tag**

Command::

  aws ec2 describe-instances --filters "Name=tag-key,Values=Owner"

For more information, see `Using Amazon EC2 Instances`_ in the *AWS Command Line Interface User Guide*.

.. _`Using Amazon EC2 Instances`: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-launch.html


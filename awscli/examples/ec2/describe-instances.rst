**To describe an Amazon EC2 instance**

Command::

  aws ec2 describe-instances --instance-ids i-1234567890abcdef0

**To describe all instances with the instance type m1.small**

Command::

  aws ec2 describe-instances --filters "Name=instance-type,Values=m1.small"

**To describe all instances with a Owner tag**

Command::

  aws ec2 describe-instances --filters "Name=tag-key,Values=Owner"

**To describe all instances with a Purpose=test tag**

Command::

  aws ec2 describe-instances --filters "Name=tag:Purpose,Values=test"

**To describe all EC2 instances that have an instance type of m1.small or m1.medium that are also in the us-west-2c Availability Zone**

Command::

  aws ec2 describe-instances --filters "Name=instance-type,Values=m1.small,m1.medium" "Name=availability-zone,Values=us-west-2c"
  
The following JSON input performs the same filtering.

Command::

  aws ec2 describe-instances --filters file://filters.json

filters.json::

  [
    {
      "Name": "instance-type",
      "Values": ["m1.small", "m1.medium"]
    },
    {
      "Name": "availability-zone",
      "Values": ["us-west-2c"]
    }
  ]

For more information, see `Using Amazon EC2 Instances`_ in the *AWS Command Line Interface User Guide*.

.. _`Using Amazon EC2 Instances`: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-launch.html


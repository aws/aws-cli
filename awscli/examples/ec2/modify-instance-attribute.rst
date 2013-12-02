**To modify the instance type**

This example modifies the instance type of the specified instance. The instance must be in the ``stopped`` state.

Command::

  aws ec2 modify-instance-attribute --instance-id i-5203422c --instance-type "{\"Value\": \"m1.small\"}"

Output::

  {
      "return": "true"
  }

**To modify the sourceDestCheck attribute**

This example sets the ``sourceDestCheck`` attribute of the specified instance to ``true``. The instance must be in a VPC.

Command::

  aws ec2 modify-instance-attribute --instance-id i-5203422c --source-dest-check "{\"Value\": true}"

Output::

  {
      "return": "true"
  }


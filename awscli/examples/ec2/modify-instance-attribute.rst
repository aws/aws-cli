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

**To modify the deleteOnTermination attribute of the root volume**

This example sets the ``deleteOnTermination`` attribute for the root volume of the specified Amazon EBS-backed instance to ``false``. By default, this attribute is ``true`` for the root volume.

Command::

  aws ec2 modify-instance-attribute --instance-id i-5203422c --block-device-mappings "[{\"DeviceName\": \"/dev/sda1\",\"Ebs\":{\"DeleteOnTermination\":false}}]"

Output::

  {
      "return": "true"
  }

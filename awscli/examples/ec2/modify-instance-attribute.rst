**To modify the instance type**

This example modifies the instance type of the specified instance. The instance must be in the ``stopped`` state. If the command succeeds, no output is returned.

Command::

  aws ec2 modify-instance-attribute --instance-id i-1234567890abcdef0 --instance-type "{\"Value\": \"m1.small\"}"

**To enable enhanced networking on an instance**

This example enables enhanced networking for the specified instance. The instance must be in the ``stopped`` state. If the command succeeds, no output is returned.

Command::

  aws ec2 modify-instance-attribute --instance-id i-1234567890abcdef0 --sriov-net-support simple

**To modify the sourceDestCheck attribute**

This example sets the ``sourceDestCheck`` attribute of the specified instance to ``true``. The instance must be in a VPC. If the command succeeds, no output is returned.

Command::

  aws ec2 modify-instance-attribute --instance-id i-1234567890abcdef0 --source-dest-check "{\"Value\": true}"

**To modify the deleteOnTermination attribute of the root volume**

This example sets the ``deleteOnTermination`` attribute for the root volume of the specified Amazon EBS-backed instance to ``false``. By default, this attribute is ``true`` for the root volume. If the command succeeds, no output is returned.

Command::

  aws ec2 modify-instance-attribute --instance-id i-1234567890abcdef0 --block-device-mappings "[{\"DeviceName\": \"/dev/sda1\",\"Ebs\":{\"DeleteOnTermination\":false}}]"

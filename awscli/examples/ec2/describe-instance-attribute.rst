**To describe the instance type**

This example describes the instance type of the specified instance.

Command::

  aws ec2 describe-instance-attribute --instance-id i-5203422c --attribute instanceType

Output::

  {
      "InstanceId": "i-5203422c"
      "InstanceType": {
          "Value": "t1.micro"
      }
  }

**To describe the disableApiTermination attribute**

This example describes the ``disableApiTermination`` attribute of the specified instance.

Command::

  aws ec2 describe-instance-attribute --instance-id i-5203422c --attribute disableApiTermination

Output::

  {
      "InstanceId": "i-5203422c"
      "DisableApiTermination": {
          "Value": "false"
      }
  }


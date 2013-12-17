**To reset the sourceDestCheck attribute**

This example resets the ``sourceDestCheck`` attribute of the specified instance. The instance must be in a VPC.

Command::

  aws ec2 reset-instance-attribute --instance-id i-5203422c --attribute sourceDestCheck

Output::

  {
      "return": "true"
  }

**To reset the kernel attribute**

This example resets the ``kernel`` attribute of the specified instance. The instance must be in the ``stopped`` state.

Command::

  aws ec2 reset-instance-attribute --instance-id i-5203422c --attribute kernel

Output::

  {
      "return": "true"
  }

**To reset the ramdisk attribute**

This example resets the ``ramdisk`` attribute of the specified instance. The instance must be in the ``stopped`` state.

Command::

  aws ec2 reset-instance-attribute --instance-id i-5203422c --attribute ramdisk

Output::

  {
      "return": "true"
  }


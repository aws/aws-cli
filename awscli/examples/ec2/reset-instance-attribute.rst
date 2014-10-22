**To reset the sourceDestCheck attribute**

This example resets the ``sourceDestCheck`` attribute of the specified instance. The instance must be in a VPC. If the command succeeds, no output is returned.

Command::

  aws ec2 reset-instance-attribute --instance-id i-5203422c --attribute sourceDestCheck

**To reset the kernel attribute**

This example resets the ``kernel`` attribute of the specified instance. The instance must be in the ``stopped`` state. If the command succeeds, no output is returned.

Command::

  aws ec2 reset-instance-attribute --instance-id i-5203422c --attribute kernel

**To reset the ramdisk attribute**

This example resets the ``ramdisk`` attribute of the specified instance. The instance must be in the ``stopped`` state. If the command succeeds, no output is returned.

Command::

  aws ec2 reset-instance-attribute --instance-id i-5203422c --attribute ramdisk

**To create an AMI from an Amazon EBS-backed instance**

This example creates an AMI from the specified instance.

Command::

  aws ec2 create-image --instance-id i-1234567890abcdef0 --name "My server" --description "An AMI for my server"

Output::

  {
      "ImageId": "ami-5731123e"
  }

This example creates an AMI and sets the --no-reboot parameter, so that the instance is not rebooted before the image is created.

Command::

  aws ec2 create-image --instance-id i-0b09a25c58929de26 --name "My server" --no-reboot

Output::

  {
    "ImageId": "ami-1a2b3c4d"
  }

**To create an AMI using a block device mapping**

Add the following parameter to your ``create-image`` command to add an Amazon EBS volume with the device name ``/dev/sdh`` and a volume size of 100::

  --block-device-mappings "[{\"DeviceName\": \"/dev/sdh\",\"Ebs\":{\"VolumeSize\":100}}]"

Add the following parameter to your ``create-image`` command to add ``ephemeral1`` as an instance store volume with the device name ``/dev/sdc``::

  --block-device-mappings "[{\"DeviceName\": \"/dev/sdc\",\"VirtualName\":\"ephemeral1\"}]"

Add the following parameter to your ``create-image`` command to omit a device included on the instance (for example, ``/dev/sdf``)::

  --block-device-mappings "[{\"DeviceName\": \"/dev/sdf\",\"NoDevice\":\"\"}]"

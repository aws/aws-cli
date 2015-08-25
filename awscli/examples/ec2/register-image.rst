**To register an AMI using a manifest file**

This example registers an AMI using the specified manifest file in Amazon S3.

Command::

  aws ec2 register-image --image-location my-s3-bucket/myimage/image.manifest.xml --name "MyImage"

Output::

  {
      "ImageId": "ami-61341708"
  }

**To add a block device mapping**

Add the following parameter to your ``register-image`` command to add an Amazon EBS volume with the device name ``/dev/sdh`` and a volume size of 100::

  --block-device-mappings "[{\"DeviceName\": \"/dev/sdh\",\"Ebs\":{\"VolumeSize\":100}}]"

Add the following parameter to your ``register-image`` command to add ``ephemeral1`` as an instance store volume with the device name ``/dev/sdc``::

  --block-device-mappings "[{\"DeviceName\": \"/dev/sdc\",\"VirtualName\":\"ephemeral1\"}]"

Add the following parameter to your ``register-image`` command to omit a device (for example, ``/dev/sdf``)::

  --block-device-mappings "[{\"DeviceName\": \"/dev/sdf\",\"NoDevice\":\"\"}]"

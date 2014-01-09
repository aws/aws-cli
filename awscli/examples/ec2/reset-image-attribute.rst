**To reset the launchPermission attribute**

This example resets the ``launchPermission`` attribute for the specified AMI to its default value. By default, AMIs are private.

Command::

  aws ec2 reset-image-attribute --image-id ami-5731123e --attribute launchPermission

Output::

  {
      "return": "true"
  }
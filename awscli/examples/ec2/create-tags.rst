**To add a tag to a resource**

This example adds the tag ``Stack=Test`` to the specified image.

Command::

  aws ec2 create-tags --resources ami-78a54011 --tags Key=Stack,Value=Test

Output::

  {
      "return": "true"
  }


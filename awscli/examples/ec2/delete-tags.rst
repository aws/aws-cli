**To delete a tag from a resource**

This example deletes the tag ``Stack=Test`` from the specified image.

Command::

  aws ec2 delete-tags --resources ami-78a54011 --tags Key=Stack,Value=Test

Output::

  {
      "return": "true"
  }


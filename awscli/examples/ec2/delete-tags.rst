**To delete a tag from a resource**

This example deletes the tag ``Stack=Test`` from the specified image. If the command succeeds, no output is returned.

Command::

  aws ec2 delete-tags --resources ami-78a54011 --tags Key=Stack,Value=Test


It's optional to specify the value for any tag with a value. If you specify a value for the key, the tag is deleted only if the tag's value matches the one you specified. If you specify the empty string as the value, the tag is deleted only if the tag's value is the empty string. The following example specifies the empty string as the value for the tag to delete.

Command::

  aws ec2 delete-tags --resources i-1234567890abcdef0 --tags Key=Name,Value=
 
This example deletes the tag with the ``purpose`` key from the specified instance, regardless of the tag's value.

Command::

  aws ec2 delete-tags --resources i-1234567890abcdef0 --tags Key=purpose
  
**To delete a tag from multiple resources**
  
This example deletes the ``Purpose=Test`` tag from a specified instance and AMI. The tag's value can be omitted from the command. If the command succeeds, no output is returned.

Command::

  aws ec2 delete-tags --resources i-1234567890abcdef0 ami-78a54011 --tags Key=Purpose

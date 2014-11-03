**To make an AMI public**

This example makes the specified AMI public. If the command succeeds, no output is returned.

Command::

  aws ec2 modify-image-attribute --image-id ami-5731123e --launch-permission "{\"Add\": [{\"Group\":\"all\"}]}"

**To make an AMI private**

This example makes the specified AMI private. If the command succeeds, no output is returned.

Command::

  aws ec2 modify-image-attribute --image-id ami-5731123e --launch-permission "{\"Remove\": [{\"Group\":\"all\"}]}"

**To grant launch permission to an AWS account**

This example grants launch permissions to the specified AWS account. If the command succeeds, no output is returned.

Command::

  aws ec2 modify-image-attribute --image-id ami-5731123e --launch-permission "{\"Add\": [{\"UserId\":\"123456789012\"}]}"

**To removes launch permission from an AWS account**

This example removes launch permissions from the specified AWS account. If the command succeeds, no output is returned.

Command::

  aws ec2 modify-image-attribute --image-id ami-5731123e --launch-permission "{\"Remove\": [{\"UserId\":\"123456789012\"}]}"

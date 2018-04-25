**To enable the longer ID format for a resource**

This example enables the longer ID format for the ``instance`` resource type. If the request is successful, no output is returned.

Command::

  aws ec2 modify-id-format --resource instance --use-long-ids

**To disable the longer ID format for a resource**

This example disables the longer ID format for the ``instance`` resource type. If the request is successful, no output is returned. 

Command::

  aws ec2 modify-id-format --resource instance --no-use-long-ids

This example enables the longer ID format for all supported resource types that are within their opt-in period. If the request is successful, no output is returned. 

Command::

  aws ec2 modify-id-format --resource all-current --use-long-ids

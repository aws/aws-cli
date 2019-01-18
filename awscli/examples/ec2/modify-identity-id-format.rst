**To enable an IAM role to use longer IDs for a resource**

This example enables the IAM role ``EC2Role`` in your AWS account to use the longer ID format for the ``instance`` resource type. If the request is successful, no output is returned.

Command::

  aws ec2 modify-identity-id-format --principal-arn arn:aws:iam::123456789012:role/EC2Role --resource instance --use-long-ids

**To enable an IAM user to use longer IDs for a resource**

This example enables the IAM user ``AdminUser`` in your AWS account to use the longer ID format for the ``volume`` resource type. If the request is successful, no output is returned.

Command::

  aws ec2 modify-identity-id-format --principal-arn arn:aws:iam::123456789012:user/AdminUser --resource volume --use-long-ids

This example enables the IAM user ``AdminUser`` in your AWS account to use the longer ID format for all supported resource types that are within their opt-in period. If the request is successful, no output is returned. 

Command::

  aws ec2 modify-identity-id-format --principal-arn arn:aws:iam::123456789012:user/AdminUser --resource all-current --use-long-ids

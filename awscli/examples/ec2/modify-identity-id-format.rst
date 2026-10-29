**Example 1: To enable an IAM role to use longer IDs for a resource**

The following ``modify-identity-id-format`` example enables the IAM role ``EC2Role`` in your AWS account to use long ID format for the ``instance`` resource type. ::

    aws ec2 modify-identity-id-format \
        --principal-arn arn:aws:iam::123456789012:role/EC2Role \
        --resource instance \
        --use-long-ids

This command produces no output.

For more information, see `Manage your Amazon EC2 resources <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/resources.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To enable an IAM user to use longer IDs for a resource**

The following ``modify-identity-id-format`` example enables the IAM user ``AdminUser`` in your AWS account to use the longer ID format for the ``volume`` resource type. ::

    aws ec2 modify-identity-id-format \
        --principal-arn arn:aws:iam::123456789012:user/AdminUser \
        --resource volume \
        --use-long-ids

This command produces no output.

The following ``modify-identity-id-format`` example enables the IAM user ``AdminUser`` in your AWS account to use the longer ID format for all supported resource types that are within their opt-in period. ::

    aws ec2 modify-identity-id-format \
        --principal-arn arn:aws:iam::123456789012:user/AdminUser \
        --resource all-current \
        --use-long-ids

This command produces no output.

For more information, see `Manage your Amazon EC2 resources <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/resources.html>`__ in the *Amazon EC2 User Guide*.

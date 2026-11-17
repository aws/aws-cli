**Example 1: To describe the ID format for an IAM role**

The following ``describe-identity-id-format`` example describes the ID format received by instances created by the IAM role ``EC2Role`` in your AWS account. ::

    aws ec2 describe-identity-id-format \
        --principal-arn arn:aws:iam::123456789012:role/my-iam-role \
        --resource instance

The following output indicates that instances created by this role receive IDs in long ID format.

Output::

    {
        "Statuses": [
            {
                "Deadline": "2016-12-15T00:00:00Z",
                "Resource": "instance",
                "UseLongIds": true
            }
        ]
    }

For more information, see `Manage your Amazon EC2 resources <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/resources.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To describe the ID format for an IAM user**

The following ``describe-identity-id-format`` example describes the ID format received by snapshots created by the IAM user ``AdminUser`` in your AWS account. ::

    aws ec2 describe-identity-id-format \
        --principal-arn arn:aws:iam::123456789012:user/AdminUser \
        --resource snapshot

The output indicates that snapshots created by this user receive IDs in long ID format.

Output::

    {
        "Statuses": [
            {
                "Deadline": "2016-12-15T00:00:00Z",
                "Resource": "snapshot",
                "UseLongIds": true
            }
        ]
    }

For more information, see `Manage your Amazon EC2 resources <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/resources.html>`__ in the *Amazon EC2 User Guide*.

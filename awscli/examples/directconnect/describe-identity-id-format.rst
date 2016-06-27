**To describe the ID format for an IAM role**

This example describes the ID format of the ``instance`` resource for the IAM role ``EC2Role`` in your AWS account. The output indicates that instances are enabled for longer IDs - instances created by this role receive longer IDs.

Command::

  aws ec2 describe-identity-id-format --principal-arn arn:aws:iam::123456789012:role/EC2Role --resource instance

Output::

  {
      "Statuses": [
          {
              "UseLongIds": true, 
              "Resource": "instance"
          }
      ]
  }

**To describe the ID format for an IAM user**

This example describes the ID format of the ``snapshot`` resource for the IAM user ``AdminUser`` in your AWS account. The output indicates that snapshots are enabled for longer IDs - snapshots created by this user receive longer IDs.

Command::

  aws ec2 describe-identity-id-format --principal-arn arn:aws:iam::123456789012:user/AdminUser --resource snapshot

Output::

  {
      "Statuses": [
          {
              "UseLongIds": true, 
              "Resource": "snapshot"
          }
      ]
  }
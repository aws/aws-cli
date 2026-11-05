**To describe IAM instance profile associations**

The following ``describe-iam-instance-profile-associations`` example describes all of your IAM instance profile associations. ::

    aws ec2 describe-iam-instance-profile-associations

Output::

    {
        "IamInstanceProfileAssociations": [
            {
                "InstanceId": "i-09eb09efa73ec1dee",
                "State": "associated",
                "AssociationId": "iip-assoc-0db249b1f25fa24b8",
                "IamInstanceProfile": {
                    "Id": "AIPAJVQN4F5WVLGCJDRGM",
                    "Arn": "arn:aws:iam::123456789012:instance-profile/admin-role"
                }
            },
            {
                "InstanceId": "i-0402909a2f4dffd14",
                "State": "associating",
                "AssociationId": "iip-assoc-0d1ec06278d29f44a",
                "IamInstanceProfile": {
                    "Id": "AGJAJVQN4F5WVLGCJABCM",
                    "Arn": "arn:aws:iam::123456789012:instance-profile/user1-role"
                }
            }
        ]
    }

For more information, see `IAM roles for Amazon EC2 <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html>`__ in the *Amazon EC2 User Guide*.

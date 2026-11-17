**To associate an IAM instance profile with an instance**

The following ``associate-iam-instance-profile`` example associates an IAM instance profile named ``admin-role`` with instance ``i-123456789abcde123``. ::

    aws ec2 associate-iam-instance-profile \
        --instance-id i-123456789abcde123 \
        --iam-instance-profile Name=admin-role

Output::

    {
        "IamInstanceProfileAssociation": {
            "InstanceId": "i-123456789abcde123",
            "State": "associating",
            "AssociationId": "iip-assoc-0e7736511a163c209",
            "IamInstanceProfile": {
                "Id": "AIPAJBLK7RKJKWDXVHIEC",
                "Arn": "arn:aws:iam::123456789012:instance-profile/admin-role"
            }
        }
    }

For more information, see `Attach an IAM role to an instance <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/attach-iam-role.html>`__ in the *Amazon EC2 User Guide*.

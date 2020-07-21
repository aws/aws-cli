**To create the required IAM role for Amazon DLM**

Amazon DLM creates the **AWSDataLifecycleManagerDefaultRole** role the first time that you create a lifecycle policy using the AWS Management Console. If you are not using the console, you can use the following command to create this role. ::

    aws dlm create-default-role

Output::

    {
        "RolePolicy": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "ec2:CreateSnapshot",
                        "ec2:CreateSnapshots",
                        "ec2:DeleteSnapshot",
                        "ec2:DescribeInstances",
                        "ec2:DescribeVolumes",
                        "ec2:DescribeSnapshots"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "ec2:CreateTags"
                    ],
                    "Resource": "arn:aws:ec2:*::snapshot/*"
                }
            ]
        },
        "Role": {
            "Path": "/",
            "RoleName": "AWSDataLifecycleManagerDefaultRole",
            "RoleId": "AROA012345678901EXAMPLE",
            "Arn": "arn:aws:iam::123456789012:role/AWSDataLifecycleManagerDefaultRole",
            "CreateDate": "2019-05-29T17:47:18Z",
            "AssumeRolePolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "dlm.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
        }
    }

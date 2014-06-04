**1. To create the default IAM role for EC2**

- Command::

    aws emr create-default-roles

- Output::

    If the role already exists then the command returns nothing.

    If the role does not exist then the output will be:

    [
        {
            "RolePolicy": {
                "Statement": [
                    {
                        "Action": [
                            "cloudwatch:*",
                            "dynamodb:*",
                            "ec2:Describe*",
                            "elasticmapreduce:Describe*",
                            "rds:Describe*",
                            "s3:*",
                            "sdb:*",
                            "sns:*",
                            "sqs:*"
                        ],
                        "Resource": [
                            "*"
                        ],
                        "Effect": "Allow"
                    }
                ]
            },
            "Role": {
                "AssumeRolePolicyDocument": {
                    "Version": "2008-10-17",
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Sid": "",
                            "Effect": "Allow",
                            "Principal": {
                                "Service": "ec2.amazonaws.com"
                            }
                        }
                    ]
                },
                "RoleId": "AROLORKUOAL65X57SBWFK",
                "CreateDate": "2014-05-07T00:02:06.154Z",
                "RoleName": "EMR_EC2_DefaultRole",
                "Path": "/",
                "Arn": "arn:aws:iam::176430881729:role/EMR_EC2_DefaultRole"
            }
        }
    ]
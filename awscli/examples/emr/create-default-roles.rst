**1. To create the default IAM roles for EMR and EC2**

- Command::

    aws emr create-default-roles

- Output::

    If both the roles already exist then the command returns nothing.

    If only one of the roles does not exist, the command returns the
    created 'Role' and the 'RolePolicy'.

    If neither of the roles exist then the output will be:

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
                "RoleId": "AROAJDKUOAL65X57SBWFK",
                "CreateDate": "2014-05-07T00:02:06.154Z",
                "RoleName": "EMR_EC2_DefaultRole",
                "Path": "/",
                "Arn": "arn:aws:iam::176430881729:role/EMR_EC2_DefaultRole"
            }
        },
        {
            "RolePolicy": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": [
                            "ec2:AuthorizeSecurityGroupIngress",
                            "ec2:CancelSpotInstanceRequests",
                            "ec2:CreateSecurityGroup",
                            "ec2:CreateTags",
                            "ec2:Describe*",
                            "ec2:DeleteTags",
                            "ec2:ModifyImageAttribute",
                            "ec2:ModifyInstanceAttribute",
                            "ec2:RequestSpotInstances",
                            "ec2:RunInstances",
                            "ec2:TerminateInstances",
                            "iam:PassRole",
                            "iam:ListRolePolicies",
                            "iam:GetRole",
                            "iam:GetRolePolicy",
                            "iam:ListInstanceProfiles",
                            "s3:Get*",
                            "s3:List*",
                            "s3:CreateBucket",
                            "sdb:BatchPutAttributes",
                            "sdb:Select"
                        ],
                        "Resource": "*",
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
                                "Service": "elasticmapreduce.amazonaws.com"
                            }
                        }
                    ]
                },
                "RoleId": "AROAJ46UH7B2XLI3RQAS4",
                "CreateDate": "2014-05-07T00:02:08.724Z",
                "RoleName": "EMR_DefaultRole",
                "Path": "/",
                "Arn": "arn:aws:iam::176430881729:role/EMR_DefaultRole"
            }
        }
    ]

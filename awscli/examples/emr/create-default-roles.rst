**1. To create the default IAM role for EC2**

- Command::

    aws emr create-default-roles

- Output::

    If the role already exists then the command returns nothing.

    If the role does not exist then the output will be:

    [
        {
            "RolePolicy": {
                "Version": "2012-10-17",
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
                                "Service": "ec2.amazonaws.com"
                            }
                        }
                    ]
                },
                "RoleId": "AROAI4UCKMKI24S7TF3C2",
                "CreateDate": "2015-05-13T00:24:23.922Z",
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
                            "ec2:DeleteTags",
                            "ec2:DescribeAvailabilityZones",
                            "ec2:DescribeAccountAttributes",
                            "ec2:DescribeInstances",
                            "ec2:DescribeKeyPairs",
                            "ec2:DescribeRouteTables",
                            "ec2:DescribeSecurityGroups",
                            "ec2:DescribeSpotInstanceRequests",
                            "ec2:DescribeSpotPriceHistory",
                            "ec2:DescribeSubnets",
                            "ec2:DescribeVpcAttributes",
                            "ec2:DescribeVpcs",
                            "ec2:ModifyImageAttribute",
                            "ec2:ModifyInstanceAttribute",
                            "ec2:RequestSpotInstances",
                            "ec2:RunInstances",
                            "ec2:TerminateInstances",
                            "iam:GetRole",
                            "iam:GetRolePolicy",
                            "iam:ListInstanceProfiles",
                            "iam:ListRolePolicies",
                            "iam:PassRole",
                            "s3:CreateBucket",
                            "s3:Get*",
                            "s3:List*",
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
                "RoleId": "AROAJV5OECHP5UQDEGBQ6",
                "CreateDate": "2015-05-13T00:24:27.048Z",
                "RoleName": "EMR_DefaultRole",
                "Path": "/",
                "Arn": "arn:aws:iam::176430881729:role/EMR_DefaultRole"
            }
        }
    ]

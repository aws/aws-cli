**To describe prefix lists**

The following ``describe-prefix-lists`` example lists all available prefix lists for the region. ::

    aws ec2 describe-prefix-lists

Output::

    {
        "PrefixLists": [
            {
                "PrefixListName": "com.amazonaws.us-west-2.s3",
                "Cidrs": [
                    "54.231.0.0/17"
                ],
                "PrefixListId": "pl-63a5400a"
            }
        ]
    }

For more information, see `AWS-managed prefix lists <https://docs.aws.amazon.com/vpc/latest/userguide/working-with-aws-managed-prefix-lists.html>`__ in the *Amazon VPC User Guide*.

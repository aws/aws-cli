**To get information about AWS Cloud9 development environments**

The following ``describe-environments`` example gets information about the specified AWS Cloud9 development environments. ::

    aws cloud9 describe-environments \
        --environment-ids 685f892f431b45c2b28cb69eadcdb0EX 349c86d4579e4e7298d500ff57a6b2EX

Output::

    {
        "environments": [
            {
                "id": "685f892f431b45c2b28cb69eadcdb0EX",
                "name": "my-demo-ec2-env",
                "description": "Created from CodeStar.",
                "type": "ec2",
                "arn": "arn:aws:cloud9:us-west-2:123456789012:environment:685f892f431b45c2b28cb69eadcdb0EX",
                "ownerArn": "arn:aws:iam::123456789012:user/MyDemoUser",
                "lifecycle": {
                    "status": "CREATED"
                }
            },
            {
                "id": "349c86d4579e4e7298d500ff57a6b2EX",
                "name": "my-demo-ssh-env",
                "description": "",
                "type": "ssh",
                "arn": "arn:aws:cloud9:us-west-2:123456789012:environment:349c86d4579e4e7298d500ff57a6b2EX",
                "ownerArn": "arn:aws:iam::123456789012:user/MyDemoUser",
                "lifecycle": {
                    "status": "CREATED"
                }
            }
        ]
    }

For more information, see `Working with environments in AWS Cloud9 <https://docs.aws.amazon.com/cloud9/latest/user-guide/environments.html>`__ in the *AWS Cloud9 User Guide*.

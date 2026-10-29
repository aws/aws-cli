**Example 1: To get information about environment members for an AWS Cloud9 development environment**

The following ``describe-environment-memberships`` example gets information about environment members for the specified AWS Cloud9 development environment. ::

    aws cloud9 describe-environment-memberships \
        --environment-id 8a34f51ce1e04a08882f1e811bd706EX

Output::

    {
        "memberships": [
            {
                "environmentId": "8a34f51ce1e04a08882f1e811bd706EX",
                "userId": "AIDAJ3LOROMOUXTBSU6EX",
                "userArn": "arn:aws:iam::123456789012:user/AnotherDemoUser",
                "permissions": "read-write"
            },
            {
                "environmentId": "8a34f51ce1e04a08882f1e811bd706EX",
                "userId": "AIDAJNUEDQAQWFELJDLEX",
                "userArn": "arn:aws:iam::123456789012:user/MyDemoUser",
                "permissions": "owner"
            }
        ]
    }

For more information, see `Working with shared environment in AWS Cloud9 <https://docs.aws.amazon.com/cloud9/latest/user-guide/share-environment.html>`__ in the *AWS Cloud9 User Guide*.

**Example 2: To get information about the owner of an AWS Cloud9 development environment**

The following ``describe-environment-memberships`` example gets information about the owner of the specified AWS Cloud9 development environment. ::

    aws cloud9 describe-environment-memberships \
        --environment-id 8a34f51ce1e04a08882f1e811bd706EX \
        --permissions owner

Output::

    {
        "memberships": [
            {
                "environmentId": "8a34f51ce1e04a08882f1e811bd706EX",
                "userId": "AIDAJNUEDQAQWFELJDLEX",
                "userArn": "arn:aws:iam::123456789012:user/MyDemoUser",
                "permissions": "owner"
            }
        ]
    }

For more information, see `Working with shared environment in AWS Cloud9 <https://docs.aws.amazon.com/cloud9/latest/user-guide/share-environment.html>`__ in the *AWS Cloud9 User Guide*.

**Example 3: To get information about an environment member for multiple AWS Cloud9 development environments**

The following ``describe-environment-memberships`` example gets information about the specified environment member for multiple AWS Cloud9 development environments. ::

    aws cloud9 describe-environment-memberships \
        --user-arn arn:aws:iam::123456789012:user/MyDemoUser

Output::

    {
        "memberships": [
            {
                "environmentId": "10a75714bd494714929e7f5ec4125aEX",
                "lastAccess": 1516213427.0,
                "userId": "AIDAJNUEDQAQWFELJDLEX",
                "userArn": "arn:aws:iam::123456789012:user/MyDemoUser",
                "permissions": "owner"
            },
            {
                "environmentId": "1980b80e5f584920801c09086667f0EX",
                "lastAccess": 1516144884.0,
                "userId": "AIDAJNUEDQAQWFELJDLEX",
                "userArn": "arn:aws:iam::123456789012:user/MyDemoUser",
                "permissions": "owner"
            }
        ]
    }

For more information, see `Working with shared environment in AWS Cloud9 <https://docs.aws.amazon.com/cloud9/latest/user-guide/share-environment.html>`__ in the *AWS Cloud9 User Guide*.

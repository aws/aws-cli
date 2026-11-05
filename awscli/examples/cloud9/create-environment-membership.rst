**To add an environment member to an AWS Cloud9 development environment**

The following ``create-environment-membership`` example adds the specified environment member to the specified AWS Cloud9 development environment. ::

    aws cloud9 create-environment-membership \
        --environment-id 8a34f51ce1e04a08882f1e811bd706EX \
        --user-arn arn:aws:iam::123456789012:user/AnotherDemoUser \
        --permissions read-write

Output::

    {
        "membership": {
            "environmentId": "8a34f51ce1e04a08882f1e811bd706EX",
            "userId": "AIDAJ3LOROMOUXTBSU6EX",
            "userArn": "arn:aws:iam::123456789012:user/AnotherDemoUser",
            "permissions": "read-write"
        }
    }

For more information, see `Working with shared environment in AWS Cloud9 <https://docs.aws.amazon.com/cloud9/latest/user-guide/share-environment.html>`__ in the *AWS Cloud9 User Guide*.

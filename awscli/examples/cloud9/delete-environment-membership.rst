**To delete an environment member from an AWS Cloud9 development environment**

The following ``delete-environment-membership`` example deletes the specified environment member from the specified AWS Cloud9 development environment. This command produces no output. ::

    aws cloud9 delete-environment-membership \
        --environment-id 8a34f51ce1e04a08882f1e811bd706EX \
        --user-arn arn:aws:iam::123456789012:user/AnotherDemoUser

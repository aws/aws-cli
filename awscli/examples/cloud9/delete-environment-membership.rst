**To delete an environment member from an AWS Cloud9 development environment**

The following ``delete-environment-membership`` example deletes the specified environment member from the specified AWS Cloud9 development environment. ::

    aws cloud9 delete-environment-membership \
        --environment-id 8a34f51ce1e04a08882f1e811bd706EX \
        --user-arn arn:aws:iam::123456789012:user/AnotherDemoUser

This command produces no output.

For more information, see `Remove another environment member <https://docs.aws.amazon.com/cloud9/latest/user-guide/share-environment-delete-member.html>`__ in the *AWS Cloud9 User Guide*.

**To change the settings of an existing AWS Cloud9 development environment**

The following ``update-environment`` example changes the specified settings of the specified existing AWS Cloud9 development environment. ::

    aws cloud9 update-environment \
        --environment-id 8a34f51ce1e04a08882f1e811bd706EX \
        --name my-changed-demo-env \
        --description "My changed demonstration development environment."

This command produces no output.

For more information, see `Changing environment settings in AWS Cloud9 <https://docs.aws.amazon.com/cloud9/latest/user-guide/change-environment.html>`__ in the *AWS Cloud9 User Guide*.

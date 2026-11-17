**To delete an AWS Cloud9 development environment**

The following ``delete-environment`` example deletes the specified AWS Cloud9 development environment. If an Amazon EC2 instance is connected to the environment, this example also terminates the instance. ::

    aws cloud9 delete-environment \
        --environment-id 8a34f51ce1e04a08882f1e811bd706EX

This command produces no output.

For more information, see `Deleting an environment in AWS Cloud9 <https://docs.aws.amazon.com/cloud9/latest/user-guide/delete-environment.html>`__ in the *AWS Cloud9 User Guide*.

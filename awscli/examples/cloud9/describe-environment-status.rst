**To get status information for an AWS Cloud9 development environment**

The following ``describe-environment-status`` example gets status information for the specified AWS Cloud9 development environment. ::

    aws cloud9 describe-environment-status \
        --environment-id 685f892f431b45c2b28cb69eadcdb0EX

Output::

    {
        "status": "ready",
        "message": "Environment is ready to use"
    }

For more information, see `Working with environments in AWS Cloud9 <https://docs.aws.amazon.com/cloud9/latest/user-guide/environments.html>`__ in the *AWS Cloud9 User Guide*.

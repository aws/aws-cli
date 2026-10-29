**To delete a repository**

The following ``delete-repository`` example deletes an AWS CodeCommit repository. ::

    aws codecommit delete-repository \
        --repository-name MyDemoRepo

Output::

    {
        "repositoryId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Delete an AWS CodeCommit repository <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-delete-repository.html#how-to-delete-repository-cli>`__ in the *AWS CodeCommit User Guide*.

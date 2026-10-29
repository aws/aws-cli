**To delete a repository**

The following ``delete-repository`` example deletes an AWS CodeCommit repository. ::

    aws codecommit delete-repository \
        --repository-name MyDemoRepo

Output::

    {
        "repositoryId": "f7579e13-b83e-4027-aaef-650c0EXAMPLE"
    }

For more information, see `Delete an AWS CodeCommit repository <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-delete-repository.html#how-to-delete-repository-cli>`__ in the *AWS CodeCommit User Guide*.

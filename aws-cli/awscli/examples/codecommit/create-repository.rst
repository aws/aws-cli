**To create a repository**

The following ``create-repository`` example creates a repository and associates it with the user's AWS account. ::

    aws codecommit create-repository \
        --repository-name MyDemoRepo \
        --repository-description "My demonstration repository"

Output::

    {
        "repositoryMetadata": {
            "repositoryName": "MyDemoRepo",
            "cloneUrlSsh": "ssh://git-codecommit.us-west-2.amazonaws.com/v1/repos/MyDemoRepo",
            "lastModifiedDate": 1444766838.027,
            "repositoryDescription": "My demonstration repository",
            "cloneUrlHttp": "https://git-codecommit.us-west-2.amazonaws.com/v1/repos/MyDemoRepo",
            "repositoryId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "Arn": "arn:aws:codecommit:us-west-2:123456789012:MyDemoRepo",
            "accountId": "123456789012"
        }
    }

For more information, see `Create an AWS CodeCommit repository <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-create-repository.html#how-to-create-repository-cli>`__ in the *AWS CodeCommit User Guide*.

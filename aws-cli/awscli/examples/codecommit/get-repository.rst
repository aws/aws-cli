**To get information about a repository**

The following ``get-repository`` example displays details about an AWS CodeCommit repository. ::

    aws codecommit get-repository \
        --repository-name MyDemoRepo

Output::

    {
        "repositoryMetadata": {
            "creationDate": 1429203623.625,
            "defaultBranch": "main",
            "repositoryName": "MyDemoRepo",
            "cloneUrlSsh": "ssh://git-codecommit.us-west-2.amazonaws.com/v1/repos/v1/repos/MyDemoRepo",
            "lastModifiedDate": 1430783812.0869999,
            "repositoryDescription": "My demonstration repository",
            "cloneUrlHttp": "https://codecommit.us-west-2.amazonaws.com/v1/repos/MyDemoRepo",
            "repositoryId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "Arn": "arn:aws:codecommit:us-west-2:123456789012:MyDemoRepo",
            "accountId": "123456789012"
        }
    }

For more information, see `View CodeCommit repository details <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-view-repository-details.html>`__ in the *AWS CodeCommit User Guide*.

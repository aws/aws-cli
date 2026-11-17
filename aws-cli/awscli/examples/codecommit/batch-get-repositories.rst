**To view details about multiple repositories**

The following ``batch-get-repositories`` example shows details about multiple AWS CodeCommit repositories. ::

    aws codecommit batch-get-repositories \
        --repository-names MyDemoRepo MyOtherDemoRepo

Output::

    {
        "repositories": [
            {
                "creationDate": 1429203623.625,
                "defaultBranch": "main",
                "repositoryName": "MyDemoRepo",
                "cloneUrlSsh": "ssh://git-codecommit.us-west-2.amazonaws.com/v1/repos/MyDemoRepo",
                "lastModifiedDate": 1430783812.0869999,
                "repositoryDescription": "My demonstration repository",
                "cloneUrlHttp": "https://codecommit.us-west-2.amazonaws.com/v1/repos/MyDemoRepo",
                "repositoryId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Arn": "arn:aws:codecommit:us-west-2:123456789012:MyDemoRepo",
                "accountId": "123456789012"
            },
            {
                "creationDate": 1429203623.627,
                "defaultBranch": "main",
                "repositoryName": "MyOtherDemoRepo",
                "cloneUrlSsh": "ssh://git-codecommit.us-west-2.amazonaws.com/v1/repos/MyOtherDemoRepo",
                "lastModifiedDate": 1430783812.0889999,
                "repositoryDescription": "My other demonstration repository",
                "cloneUrlHttp": "https://codecommit.us-west-2.amazonaws.com/v1/repos/MyOtherDemoRepo",
                "repositoryId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Arn": "arn:aws:codecommit:us-west-2:123456789012:MyOtherDemoRepo",
                "accountId": "123456789012"
            }
        ],
        "repositoriesNotFound": []
    }

For more information, see `View CodeCommit repository details <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-view-repository-details.html#how-to-view-repository-details-with-names-cli>`__ in the *AWS CodeCommit User Guide*.

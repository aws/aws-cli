**To view a list of repositories**

The following ``list-repositories`` example lists all AWS CodeCommit repositories associated with the user's AWS account. ::

    aws codecommit list-repositories

Output::

    {
        "repositories": [
            {
                "repositoryName": "MyDemoRepo",
                "repositoryId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            },
            {
                "repositoryName": "MyOtherDemoRepo",
                "repositoryId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            }
        ]
    }

For more information, see `View CodeCommit repository details <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-view-repository-details.html>`__ in the *AWS CodeCommit User Guide*.

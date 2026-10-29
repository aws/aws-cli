**To view a list of repositories**

The following ``list-repositories`` example lists all AWS CodeCommit repositories associated with the user's AWS account. ::

    aws codecommit list-repositories

Output::

    {
        "repositories": [
            {
                "repositoryName": "MyDemoRepo",
                "repositoryId": "f7579e13-b83e-4027-aaef-650c0EXAMPLE"
            },
            {
                "repositoryName": "MyOtherDemoRepo",
                "repositoryId": "cfc29ac4-b0cb-44dc-9990-f6f51EXAMPLE"
            }
        ]
    }

For more information, see `View CodeCommit repository details <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-view-repository-details.html>`__ in the *AWS CodeCommit User Guide*.

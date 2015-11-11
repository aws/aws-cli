**To view details about multiple repositories**

This example shows details about multiple AWS CodeCommit repositories.

Command::

  aws codecommit batch-get-repositories --repository-names MyDemoRepo MyOtherDemoRepo

Output::

  {
        "repositories": [
             {
                "creationDate": 1429203623.625,
                "defaultBranch": "master",
                "repositoryName": "MyDemoRepo",
                "cloneUrlSsh": "ssh://ssh://git-codecommit.us-east-1.amazonaws.com/v1/repos//v1/repos/MyDemoRepo",
                "lastModifiedDate": 1430783812.0869999,
                "repositoryDescription": "My demonstration repository",
                "cloneUrlHttp": "https://codecommit.us-east-1.amazonaws.com/v1/repos/MyDemoRepo",
                "repositoryId": "f7579e13-b83e-4027-aaef-650c0EXAMPLE",
                "Arn": "arn:aws:codecommit:us-east-1:111111111111EXAMPLE:MyDemoRepo",
                "accountId": "111111111111"
            },
            {
                "creationDate": 1429203623.627,
                "defaultBranch": "master",
                "repositoryName": "MyOtherDemoRepo",
                "cloneUrlSsh": "ssh://ssh://git-codecommit.us-east-1.amazonaws.com/v1/repos//v1/repos/MyOtherDemoRepo",
                "lastModifiedDate": 1430783812.0889999,
                "repositoryDescription": "My other demonstration repository",
                "cloneUrlHttp": "https://codecommit.us-east-1.amazonaws.com/v1/repos/MyOtherDemoRepo",
                "repositoryId": "cfc29ac4-b0cb-44dc-9990-f6f51EXAMPLE",
                "Arn": "arn:aws:codecommit:us-east-1:111111111111EXAMPLE:MyOtherDemoRepo",
                "accountId": "111111111111"
            }
        ],
        "repositoriesNotFound": []
  }
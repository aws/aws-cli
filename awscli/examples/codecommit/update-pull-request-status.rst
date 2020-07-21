**To change the status of a pull request**

This example demonstrates how to to change the status of a pull request with the ID of '42' to a status of 'CLOSED' in an AWS CodeCommit repository named 'MyDemoRepo'::

  aws codecommit update-pull-request-status --pull-request-id 42 --pull-request-status CLOSED

Output::

  {
   "pullRequest": { 
      "authorArn": "arn:aws:iam::111111111111:user/Jane_Doe",
      "clientRequestToken": "123Example",
      "creationDate": 1508962823.165,
      "description": "A code review of the new feature I just added to the service.",
      "lastActivityDate": 1508442444.12,
      "pullRequestId": "42",
      "pullRequestStatus": "CLOSED",
      "pullRequestTargets": [ 
         { 
            "destinationCommit": "5d036259EXAMPLE",
            "destinationReference": "refs/heads/master",
            "mergeMetadata": { 
               "isMerged": false,
            },
            "repositoryName": "MyDemoRepo",
            "sourceCommit": "317f8570EXAMPLE",
            "sourceReference": "refs/heads/jane-branch"
         }
      ],
      "title": "Pronunciation difficulty analyzer"
    }
  }

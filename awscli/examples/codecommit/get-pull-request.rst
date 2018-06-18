**To view details of a pull request**

This example demonstrates how to view information about a pull request with the ID of '42'::

  aws codecommit get-pull-request --pull-request-id 42

Output::

  {
   "pullRequest": { 
      "authorArn": "arn:aws:iam::111111111111:user/Jane_Doe",
      "title": "Pronunciation difficulty analyzer"
      "pullRequestTargets": [ 
         { 
            "destinationReference": "refs/heads/master",
            "destinationCommit": "5d036259EXAMPLE",
            "sourceReference": "refs/heads/jane-branch"
            "sourceCommit": "317f8570EXAMPLE",
            "repositoryName": "MyDemoRepo",
            "mergeMetadata": { 
               "isMerged": false,
            }, 
         }
      ],
      "lastActivityDate": 1508442444,
      "pullRequestId": "42", 
      "clientRequestToken": "123Example",
      "pullRequestStatus": "OPEN",
      "creationDate": 1508962823,
      "description": "A code review of the new feature I just added to the service.",
    }
  }
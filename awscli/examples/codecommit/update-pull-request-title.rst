**To change the title of a pull request**

This example demonstrates how to change the title of a pull request with the ID of '47'::

  aws codecommit update-pull-request-title --pull-request-id 47 --title "Consolidation of global variables - updated review"

Output::

  {
   "pullRequest": { 
      "authorArn": "arn:aws:iam::111111111111:user/Li_Juan",
      "clientRequestToken": "",
      "creationDate": 1508530823.12,
      "description": "Review the latest changes and updates to the global variables. I have updated this request with some changes, including removing some unused variables.",
      "lastActivityDate": 1508372657.188,
      "pullRequestId": "47",
      "pullRequestStatus": "OPEN",
      "pullRequestTargets": [ 
         { 
            "destinationCommit": "9f31c968EXAMPLE",
            "destinationReference": "refs/heads/master",
            "mergeMetadata": { 
               "isMerged": false,
            },
            "repositoryName": "MyDemoRepo",
            "sourceCommit": "99132ab0EXAMPLE",
            "sourceReference": "refs/heads/variables-branch"
         }
      ],
      "title": "Consolidation of global variables - updated review"
    }
  }

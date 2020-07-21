**To merge and close a pull request**

This example demonstrates how to merge and close a pull request with the ID of '47' and a source commit ID of '99132ab0EXAMPLE' in a repository named 'MyDemoRepo'::

  aws codecommit merge-pull-request-by-fast-forward --pull-request-id 47 --source-commit-id 99132ab0EXAMPLE --repository-name MyDemoRepo 

Output::

  {
   "pullRequest": { 
      "authorArn": "arn:aws:iam::111111111111:user/Li_Juan",
      "clientRequestToken": "",
      "creationDate": 1508530823.142,
      "description": "Review the latest changes and updates to the global variables",
      "lastActivityDate": 1508887223.155,
      "pullRequestId": "47",
      "pullRequestStatus": "CLOSED",
      "pullRequestTargets": [ 
         { 
            "destinationCommit": "9f31c968EXAMPLE",
            "destinationReference": "refs/heads/master",
            "mergeMetadata": { 
               "isMerged": true,
               "mergedBy": "arn:aws:iam::111111111111:user/Mary_Major"
            },
            "repositoryName": "MyDemoRepo",
            "sourceCommit": "99132ab0EXAMPLE",
            "sourceReference": "refs/heads/variables-branch"
         }
      ],
      "title": "Consolidation of global variables"
    }
  }
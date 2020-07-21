**To create a pull request**

The following ``create-pull-request`` example creates a pull request named 'My Pull Request' with a description of 'Please review these changes by Tuesday' that targets the 'MyNewBranch' source branch and is to be merged to the default branch 'master' in an AWS CodeCommit repository named 'MyDemoRepo'. ::

    aws codecommit create-pull-request \
        --title "My Pull Request" \
        --description "Please review these changes by Tuesday" \
        --client-request-token 123Example \
        --targets repositoryName=MyDemoRepo,sourceReference=MyNewBranch 

Output::

    {
        "pullRequest": { 
            "authorArn": "arn:aws:iam::111111111111:user/Jane_Doe",
            "clientRequestToken": "123Example",
            "creationDate": 1508962823.285,
            "description": "Please review these changes by Tuesday",
            "lastActivityDate": 1508962823.285,
            "pullRequestId": "42",
            "pullRequestStatus": "OPEN",
            "pullRequestTargets": [ 
               { 
                    "destinationCommit": "5d036259EXAMPLE",
                    "destinationReference": "refs/heads/master",
                    "mergeMetadata": { 
                        "isMerged": false,
                    },
                    "repositoryName": "MyDemoRepo",
                    "sourceCommit": "317f8570EXAMPLE",
                    "sourceReference": "refs/heads/MyNewBranch"
                }
            ],
            "title": "My Pull Request"
        }
    }

**To merge a pull request using the three-way merge strategy**

The following ``merge-pull-request-by-three-way`` example merges and closes the specified pull request using the default options for conflict detail and conflict resolution strategy in a repository named ``MyDemoRepo``. ::

    aws codecommit merge-pull-request-by-three-way \
        --pull-request-id 47 \
        --source-commit-id 99132ab0EXAMPLE \
        --repository-name MyDemoRepo \
        --name "Maria Garcia" \
        --email "maria_garcia@example.com" \
        --commit-message "Merging pull request 47 by three-way with default options"

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
                        "mergedBy": "arn:aws:iam::111111111111:user/Maria_Garcia"
                    },
                    "repositoryName": "MyDemoRepo",
                    "sourceCommit": "99132ab0EXAMPLE",
                    "sourceReference": "refs/heads/variables-branch"
                }
            ],
            "title": "Consolidation of global variables"
        }
    }

For more information, see `Merge a Pull Request <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-merge-pull-request.html#merge-pull-request-by-three-way>`__ in the *AWS CodeCommit User Guide*.

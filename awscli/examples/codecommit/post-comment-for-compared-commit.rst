**To create a comment on a commit**

The following ``post-comment-for-compared-commit`` example adds the comment ``"Can you add a test case for this?"`` on the change to the ``cl_sample.js`` file in the comparison between two commits in a repository named ``MyDemoRepo``. ::

    aws codecommit post-comment-for-compared-commit \
        --repository-name MyDemoRepo \
        --before-commit-id 317f8570EXAMPLE \
        --after-commit-id 5d036259EXAMPLE \
        --client-request-token 123Example \
        --content "Can you add a test case for this?" \
        --location filePath=cl_sample.js,filePosition=1232,relativeFileVersion=AFTER

Output::

    {
        "afterBlobId": "1f330709EXAMPLE",
        "afterCommitId": "317f8570EXAMPLE",
        "beforeBlobId": "80906a4cEXAMPLE",
        "beforeCommitId": "6e147360EXAMPLE",
        "comment": {
            "authorArn": "arn:aws:iam::123456789012:user/Li_Juan",
            "clientRequestToken": "",
            "commentId": "553b509bEXAMPLE56198325",
            "content": "Can you add a test case for this?",
            "creationDate": 1508369612.203,
            "deleted": false,
            "inReplyTo": "abc123-EXAMPLE",
            "lastModifiedDate": 1508369612.203,
            "callerReactions": [],
            "reactionCounts": {}
        },
        "location": {
            "filePath": "cl_sample.js",
            "filePosition": 1232,
            "relativeFileVersion": "AFTER"
        },
        "repositoryName": "MyDemoRepo"
    }

For more information, see `Comment on a commit in AWS CodeCommit <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-commit-comment.html>`__ in the *AWS CodeCommit User Guide*.

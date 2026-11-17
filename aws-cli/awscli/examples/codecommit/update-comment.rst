**To update a comment on a commit**

The following ``update-comment`` example adds the content ``"Fixed as requested. I'll update the pull request."`` to a comment with an ID of ``442b498bEXAMPLE5756813``. ::

    aws codecommit update-comment \
        --comment-id 442b498bEXAMPLE5756813 \
        --content "Fixed as requested. I'll update the pull request."

Output::

    {
        "comment": {
            "authorArn": "arn:aws:iam::123456789012:user/Li_Juan",
            "clientRequestToken": "",
            "commentId": "442b498bEXAMPLE5756813",
            "content": "Fixed as requested. I'll update the pull request.",
            "creationDate": 1508369929.783,
            "deleted": false,
            "lastModifiedDate": 1508369929.287,
            "callerReactions": [],
            "reactionCounts": 
                {
                    "THUMBSUP" : 2
                }
        }
    }

For more information, see `Comment on a commit in AWS CodeCommit <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-commit-comment.html>`__ in the *AWS CodeCommit User Guide*.

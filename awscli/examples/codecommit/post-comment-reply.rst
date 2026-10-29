**To reply to a comment on a commit or in a pull request**

The following ``post-comment-reply`` example adds the reply ``"Good catch. I'll remove them."`` to the comment with the system-generated ID of ``abcd1234EXAMPLEb5678efgh``. ::

    aws codecommit post-comment-reply \
        --in-reply-to abcd1234EXAMPLEb5678efgh \
        --content "Good catch. I'll remove them." \
        --client-request-token 123Example

Output::

    {
        "comment": {
            "authorArn": "arn:aws:iam::123456789012:user/Li_Juan",
            "clientRequestToken": "123Example",
            "commentId": "442b498bEXAMPLE5756813",
            "content": "Good catch. I'll remove them.",
            "creationDate": 1508369829.136,
            "deleted": false,
            "inReplyTo": "abcd1234EXAMPLEb5678efgh",
            "lastModifiedDate": 150836912.221,
            "callerReactions": [],
            "reactionCounts": {}
        }
    }

For more information, see `Comment on a commit in AWS CodeCommit <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-commit-comment.html>`__ in the *AWS CodeCommit User Guide*.

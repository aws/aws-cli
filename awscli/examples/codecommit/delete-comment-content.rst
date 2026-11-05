**To delete the content of a comment**

The following ``delete-comment-content`` example deletes the content of a comment with the system-generated ID of ``ff30b348EXAMPLEb9aa670f``. You can only delete the content of a comment if you created the comment. ::

    aws codecommit delete-comment-content \
        --comment-id ff30b348EXAMPLEb9aa670f

Output::

    {
        "comment": { 
            "creationDate": 1508369768.142,  
            "deleted": true,
            "lastModifiedDate": 1508369842.278,
            "clientRequestToken": "123Example",
            "commentId": "ff30b348EXAMPLEb9aa670f",
            "authorArn": "arn:aws:iam::123456789012:user/Li_Juan",
            "callerReactions": [],
            "reactionCounts": 
            {
                "CLAP" : 1
            }
        } 
    }

For more information, see `Comment on a commit in AWS CodeCommit <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-commit-comment.html#how-to-commit-comment-cli-commit-delete>`__ in the *AWS CodeCommit User Guide*.

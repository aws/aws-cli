**To invite member accounts to a behavior graph**

The following ``create-members`` example invites two AWS accounts to become member accounts in the specified behavior graph. For each account, the request provides the AWS account ID and the account root user email address. The request also includes a custom message to insert into the invitation email. ::

    aws detective create-members \
        --accounts AccountId=444455556666,EmailAddress=mmajor@example.com AccountId=123456789012,EmailAddress=jstiles@example.com \
        --graph-arn arn:aws:detective:us-east-1:111122223333:graph:123412341234 \
        --message "This is Paul Santos. I need to add your account to the data we use for security investigation in Amazon Detective. If you have any questions, contact me at psantos@example.com."

Output::

    {
        "Members": [ 
        { 
            "AccountId": "444455556666",
            "EmailAddress": "mmajor@example.com",
            "GraphArn": "arn:aws:detective:us-east-1:111122223333:graph:123412341234",
            "InvitedTime": 1579826107000,
            "MasterId": "111122223333",
            "Status": "INVITED",
            "UpdatedTime": 1579826107000
       },
       { 
            "AccountId": "123456789012",
            "EmailAddress": "jstiles@example.com",
            "GraphArn": "arn:aws:detective:us-east-1:111122223333:graph:123412341234",
            "InvitedTime": 1579826107000,
            "MasterId": "111122223333",
            "Status": "VERIFICATION_IN_PROGRESS",
            "UpdatedTime": 1579826107000
         }
        ],
        "UnprocessedAccounts": [ ]
    }

For more information, see `Inviting Member Accounts to a Behavior Graph <https://docs.aws.amazon.com/detective/latest/adminguide/graph-master-add-member-accounts.html>`__ in the *Amazon Detective Administration Guide*.

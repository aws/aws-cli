**To list the member accounts in a behavior graph**

The following ``list-members`` example retrieves the invited and enabled member accounts for the specified behavior graph. The results do not include member accounts that were removed. ::

    aws detective list-members \
        --graph-arn arn:aws:detective:us-east-1:111122223333:graph:123412341234

Output::

    {
        "MemberDetails": [ 
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
            "Status": "ENABLED",
            "UpdatedTime": 1579973711000
        }
        ]
    }

For more information, see `Viewing the List of Accounts in a Behavior Graph <https://docs.aws.amazon.com/detective/latest/adminguide/graph-master-view-accounts.html>`__ in the *Amazon Detective Administration Guide*.

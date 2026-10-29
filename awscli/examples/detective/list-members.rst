**To list the member accounts in a behavior graph**

The following ``list-members`` example retrieves the invited and enabled member accounts for the behavior graph ``arn:aws:detective:us-east-1:111122223333:graph:123412341234``. The results do not include member accounts that were removed. ::

    aws detective list-members \
        --graph-arn arn:aws:detective:us-east-1:111122223333:graph:123412341234

Output::

    {
        "MemberDetails": [
            {
                "AccountId": "444455556666",
                "AdministratorId": "111122223333",
                "EmailAddress": "mmajor@example.com",
                "GraphArn": "arn:aws:detective:us-east-1:111122223333:graph:123412341234",
                "InvitedTime": "2020-01-24T00:35:07.000000+00:00",
                "MasterId": "111122223333",
                "Status": "INVITED",
                "UpdatedTime": "2020-01-24T00:35:07.000000+00:00"
            },
            { 
                "AccountId": "123456789012",
                "AdministratorId": "111122223333",
                "EmailAddress": "jstiles@example.com",
                "GraphArn": "arn:aws:detective:us-east-1:111122223333:graph:123412341234",
                "InvitedTime": "2020-01-24T00:35:07.000000+00:00",
                "MasterId": "111122223333",
                "PercentOfGraphUtilization": 2,
                "PercentOfGraphUtilizationUpdatedTime": "2020-04-07T19:30:43.000000+00:00",
                "Status": "ENABLED",
                "UpdatedTime": "2020-01-25T17:35:11.000000+00:00",
                "VolumeUsageInBytes": 200,
                "VolumeUsageUpdatedTime": "2020-04-07T19:30:43.000000+00:00"
            }
        ]
    }

For more information, see `Viewing the list of accounts in a behavior graph <https://docs.aws.amazon.com/detective/latest/adminguide/graph-admin-view-accounts.html>`__ in the *Amazon Detective Administration Guide*.
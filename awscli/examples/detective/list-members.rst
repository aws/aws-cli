**To list the member accounts in a behavior graph**

The following ``list-members`` example retrieves the invited and enabled member accounts for the behavior graph ``arn:aws:detective:us-west-2:123456789111:graph:027c7c4610ea4aacaf0b883093cab899``. The results do not include member accounts that were removed. ::

    aws detective list-members \
        --graph-arn arn:aws:detective:us-west-2:123456789111:graph:027c7c4610ea4aacaf0b883093cab899

Output::

    {
        "MemberDetails": [
            {
                "AccountId": "123456789222",
                "AdministratorId": "123456789111",
                "EmailAddress": "mmajor@example.com",
                "GraphArn": "arn:aws:detective:us-west-2:123456789111:graph:027c7c4610ea4aacaf0b883093cab899",
                "InvitedTime": "2020-01-24T00:35:07.000000+00:00",
                "MasterId": "123456789111",
                "Status": "INVITED",
                "UpdatedTime": "2020-01-24T00:35:07.000000+00:00"
            },
            { 
                "AccountId": "123456789012",
                "AdministratorId": "123456789111",
                "EmailAddress": "jstiles@example.com",
                "GraphArn": "arn:aws:detective:us-west-2:123456789111:graph:027c7c4610ea4aacaf0b883093cab899",
                "InvitedTime": "2020-01-24T00:35:07.000000+00:00",
                "MasterId": "123456789111",
                "PercentOfGraphUtilization": 2,
                "PercentOfGraphUtilizationUpdatedTime": "2020-04-07T19:30:43.000000+00:00",
                "Status": "ENABLED",
                "UpdatedTime": "2020-01-25T17:35:11.000000+00:00",
                "VolumeUsageInBytes": 200,
                "VolumeUsageUpdatedTime": "2020-04-07T19:30:43.000000+00:00"
            }
        ]
    }

For more information, see `Viewing the list of accounts <https://docs.aws.amazon.com/detective/latest/userguide/accounts-view-list.html>`__ in the *Amazon Detective Administration Guide*.
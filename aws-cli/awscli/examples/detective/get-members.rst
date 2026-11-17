**To retrieve information about selected behavior graph member accounts**

The following ``get-members`` example retrieves information about two member accounts in the behavior graph arn:aws:detective:us-west-2:123456789111:graph:123412341234. For the two accounts, the request provides the AWS account IDs. ::

    aws detective get-members \
        --account-ids 123456789222 123456789012 \
        --graph-arn arn:aws:detective:us-west-2:123456789111:graph:027c7c4610ea4aacaf0b883093cab899

Output::

    {
        "MemberDetails": [
            {
                "AccountId": "123456789222",
                "AdministratorId": "123456789111",
                "EmailAddress": "mmajor@example.com",
                "GraphArn": "arn:aws:detective:us-west-2:123456789111:graph:027c7c4610ea4aacaf0b883093cab899",
                "InvitedTime": "2020-01-24T00:35:07+00:00",
                "MasterId": "123456789111",
                "Status": "INVITED",
                "UpdatedTime": "2020-01-24T00:35:07+00:00"
            },
            {
                "AccountId": "123456789012",
                "AdministratorId": "123456789111",
                "EmailAddress": "jstiles@example.com",
                "GraphArn": "arn:aws:detective:us-west-2:123456789111:graph:027c7c4610ea4aacaf0b883093cab899",
                "InvitedTime": "2020-01-24T00:35:07+00:00",
                "MasterId": "123456789111",
                "Status": "INVITED",
                "UpdatedTime": "2020-01-24T00:35:07+00:00"
            }
        ],
        "UnprocessedAccounts": []
    }

For more information, see `Viewing the list of accounts <https://docs.aws.amazon.com/detective/latest/userguide/accounts-view-list.html>`__ in the *Amazon Detective User Guide*.

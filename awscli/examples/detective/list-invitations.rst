**To view a list of behavior graphs that an account is a member of or is invited to**

The following ``list-invitations`` example retrieves the behavior graphs that the calling account has been invited to. The results include only open and accepted invitations. They do not include rejected invitations or removed memberships. ::

    aws detective list-invitations

Output::

    {
        "Invitations": [ 
        { 
            "AccountId": "123456789222",
            "AdministratorId": "123456789111",
            "EmailAddress": "mmajor@example.com",
            "GraphArn": "arn:aws:detective:us-west-2:123456789111:graph:027c7c4610ea4aacaf0b883093cab899",
            "InvitedTime": "2020-01-24T00:35:07+00:00",
            "MasterId": "123456789111",
            "Status": "INVITED",
            "UpdatedTime": "2020-01-24T00:35:07+00:00"
        }
    ]
    }

For more information, see `Viewing your list of behavior graph invitations <https://docs.aws.amazon.com/detective/latest/userguide/member-view-graph-invitations.html>`__ in the *Amazon Detective User Guide*.

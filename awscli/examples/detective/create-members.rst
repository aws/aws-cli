**Example 1: To invite member accounts to a behavior graph**

The following ``create-members`` example invites two AWS accounts to become member accounts in the behavior graph arn:aws:detective:us-west-2:123456789111:graph:123412341234. For each account, the request provides the AWS account ID and the account root user email address. The request includes a custom message to insert into the invitation email. ::

    aws detective create-members \
        --accounts AccountId=123456789222,EmailAddress=mmajor@example.com AccountId=123456789012,EmailAddress=jstiles@example.com \
        --graph-arn arn:aws:detective:us-west-2:123456789111:graph:027c7c4610ea4aacaf0b883093cab899 \
        --message "This is Paul Santos. I need to add your account to the data we use for security investigation in Amazon Detective. If you have any questions, contact me at psantos@example.com."

Output::

    {
        "Members": [
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
                "Status": "VERIFICATION_IN_PROGRESS",
                "UpdatedTime": "2020-01-24T00:35:07+00:00"
            }
        ],
        "UnprocessedAccounts": [ ]
    }

For more information, see `Inviting individual accounts to a behavior graph <https://docs.aws.amazon.com/detective/latest/userguide/accounts-invited-members-add-individual.html>`__ in the *Amazon Detective User Guide*.

**Example 2: To invite member accounts without sending invitation emails**

The following ``create-members`` example invites two AWS accounts to become member accounts in the behavior graph arn:aws:detective:us-west-2:123456789111:graph:123412341234. For each account, the request provides the AWS account ID and the account root user email address. The member accounts do not receive invitation emails. ::

    aws detective create-members \
        --accounts AccountId=123456789222,EmailAddress=mmajor@example.com AccountId=123456789012,EmailAddress=jstiles@example.com \
        --graph-arn arn:aws:detective:us-west-2:123456789111:graph:027c7c4610ea4aacaf0b883093cab899 \
        --disable-email-notification

Output::

    {
        "Members": [
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
                "Status": "VERIFICATION_IN_PROGRESS",
                "UpdatedTime": "2020-01-24T00:35:07+00:00"
            }
        ],
        "UnprocessedAccounts": [ ]
    }

For more information, see `Inviting individual accounts to a behavior graph <https://docs.aws.amazon.com/detective/latest/userguide/accounts-invited-members-add-individual.html>`__ in the *Amazon Detective User Guide*.

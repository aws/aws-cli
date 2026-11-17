**To remove member accounts from a behavior graph**

The following ``delete-members`` example removes two member accounts from the behavior graph arn:aws:detective:us-west-2:123456789111:graph:123412341234. To identify the accounts, the request provides the AWS account IDs. ::

    aws detective delete-members \
        --account-ids 123456789222 123456789012 \
        --graph-arn arn:aws:detective:us-west-2:123456789111:graph:027c7c4610ea4aacaf0b883093cab899

Output::

    {
        "AccountIds": [ "123456789222", "123456789012" ],
        "UnprocessedAccounts": [ ]
    }

For more information, see `Removing member accounts from a behavior graph <https://docs.aws.amazon.com/detective/latest/userguide/accounts-invited-remove.html>`__ in the *Amazon Detective User Guide*.

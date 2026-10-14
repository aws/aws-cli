**To list staging accounts**

The following ``list-staging-accounts`` example lists the staging accounts associated with your AWS Elastic Disaster Recovery configuration. ::

    aws drs list-staging-accounts

Output::

    {
        "accounts": [
            {
                "accountID": "123456789012"
            }
        ]
    }

For more information, see `AWS Elastic Disaster Recovery network requirements <https://docs.aws.amazon.com/drs/latest/userguide/network-requirements.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.

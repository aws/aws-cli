**To describe account attributes**

The following ``describe-account-attributes`` example lists the attributes for your AWS account. ::

    aws dms describe-account-attributes

Output::

    {
        "AccountQuotas": [
            {
                "AccountQuotaName": "ReplicationInstances",
                "Used": 1,
                "Max": 20
            },
            {
                "AccountQuotaName": "AllocatedStorage",
                "Used": 5,
                "Max": 10000
            }
        ],
        "UniqueAccountIdentifier": "cqahfbfy5xee"
    }

For more information, see `Quotas for AWS Database Migration Service <https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Limits.html>`__ in the *AWS Database Migration Service User Guide*.

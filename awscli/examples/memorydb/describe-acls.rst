**To return a list of ACLs**

The following ``describe-acls`` example returns a list of ACLs. ::

    aws memorydb describe-acls

Output::

    {
        "ACLs": [
            {
                "Name": "open-access",
                "Status": "active",
                "UserNames": [
                    "default"
                ],
                "MinimumEngineVersion": "6.2",
                "Clusters": [],
                "ARN": "arn:aws:memorydb:us-west-2:491658xxxxxx:acl/open-access"
            },
            {
                "Name": "my-acl",
                "Status": "active",
                "UserNames": [],
                "MinimumEngineVersion": "6.2",
                "Clusters": [
                    "my-cluster"
                ],
                "ARN": "arn:aws:memorydb:us-west-2:49165xxxxxxx:acl/my-acl"
            }
        ]
    }

For more information, see `Authenticating users with Access Control Lists <https://docs.aws.amazon.com/memorydb/latest/devguide/clusters.acls.html>`__ in the *MemoryDB User Guide*.

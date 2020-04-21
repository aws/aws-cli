**To remove tags from a resource group**

The following ``untags`` example removes any tag with the specified key from the resource group itself, not its members. ::

    aws resource-groups untag \
        --arn arn:aws:resource-groups:us-west-2:123456789012:group/tbq-WebServer \
        --keys QueryType

Output::

    {
        "Arn": "arn:aws:resource-groups:us-west-2:123456789012:group/tbq-WebServer",
        "Keys": [
            "QueryType"
        ]
    }

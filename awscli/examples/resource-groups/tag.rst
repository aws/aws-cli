**To attach a tag to a resource group**

The following ``tag`` example attaches the specified tag key and value pairs to the specified resource group (the group itself, not its members). ::

    aws resource-groups tag \
        --tags QueryType=tags,QueryResources=ec2-instances \
        --arn arn:aws:resource-groups:us-west-2:128716708097:group/tbq-WebServer

Output::

    {
        "Arn": "arn:aws:resource-groups:us-west-2:128716708097:group/tbq-WebServer",
        "Tags": {
            "QueryType": "tags",
            "QueryResources": "ec2-instances"
        }
    }

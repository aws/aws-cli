**To view the details of a container**

The following ``describe-container`` example displays the details of the specified container. ::

    aws mediastore describe-container \
        --container-name ExampleContainer

Output::

    {
        "Container": {
            "CreationTime": 1563558086,
            "AccessLoggingEnabled": false,
            "ARN": "arn:aws:mediastore:us-west-2:123456789012:container/ExampleContainer",
            "Status": "ACTIVE",
            "Name": "ExampleContainer",
            "Endpoint": "https://aaabbbcccdddee.data.mediastore.us-west-2.amazonaws.com"
        }
    }

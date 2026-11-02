**To create a container**

The following ``create-container`` example creates a new, empty container. ::

    aws mediastore create-container \
        --container-name ExampleContainer

Output::

    {
        "Container": {
            "AccessLoggingEnabled": false,
            "CreationTime": 1563557265,
            "Name": "ExampleContainer",
            "Status": "CREATING",
            "ARN": "arn:aws:mediastore:us-west-2:123456789012:container/ExampleContainer"
        }
    }

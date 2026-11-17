**To view a list of containers**

The following ``list-containers`` example displays a list of all containers that are associated with your account. ::

    aws mediastore list-containers

Output::

    {
        "Containers": [
            {
                "CreationTime": 1505317931,
                "Endpoint": "https://aaabbbcccdddee.data.mediastore.us-west-2.amazonaws.com",
                "Status": "ACTIVE",
                "ARN": "arn:aws:mediastore:us-west-2:123456789012:container/ExampleLiveDemo",
                "AccessLoggingEnabled": false,
                "Name": "ExampleLiveDemo"
            },
            {
                "CreationTime": 1506528818,
                "Endpoint": "https://fffggghhhiiijj.data.mediastore.us-west-2.amazonaws.com",
                "Status": "ACTIVE",
                "ARN": "arn:aws:mediastore:us-west-2:123456789012:container/ExampleContainer",
                "AccessLoggingEnabled": false,
                "Name": "ExampleContainer"
            }
        ]
    }

**To view the list of notification hubs**

The following ``list-notification-hubs`` example displays the list of notification hubs. ::

    aws notifications list-notification-hubs 
    
Output::
    
    {
        "notificationHubs": [
            {
                "notificationHubRegion": "us-east-1",
                "statusSummary": {
                    "status": "ACTIVE",
                    "reason": ""
                },
                "creationTime": "2023-06-16T07:16:35.164000+00:00",
                "lastActivationTime": "2023-06-16T07:16:35.251000+00:00"
            },
            {
                "notificationHubRegion": "ap-southeast-2",
                "statusSummary": {
                    "status": "ACTIVE",
                    "reason": ""
                },
                "creationTime": "2024-09-31T04:06:57.879000+00:00",
                "lastActivationTime": "2024-09-31T04:06:59.946000+00:00"
            }
        ]
    }
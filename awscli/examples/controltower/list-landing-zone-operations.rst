**To list Control Tower landing zone operations**

The following ``list-landing-zone-operations`` example lists AWS Control Tower landing zone operations. ::

    aws controltower list-landing-zone-operations

Output::

    {
        "landingZoneOperations": [
            {
                "operationIdentifier": "202ee056-5147-49fd-a7ad-8161e3bf043a",
                "operationType": "RESET",
                "status": "SUCCEEDED"
            },
            {
                "operationIdentifier": "dbd4a4b1-baf9-48cc-bd71-6b923d0f2339",
                "operationType": "RESET",
                "status": "SUCCEEDED"
            },
            {
                "operationIdentifier": "e6261ab8-3247-4052-af31-1afe7bb0593e",
                "operationType": "UPDATE",
                "status": "SUCCEEDED"
            },
            {
                "operationIdentifier": "507c6c87-89a8-435f-8697-b257a800f129",
                "operationType": "UPDATE",
                "status": "SUCCEEDED"
            }
        ]
    }

For more information, see `Getting started with AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/userguide/getting-started-with-control-tower.html>`__ in the *AWS Control Tower User Guide*.
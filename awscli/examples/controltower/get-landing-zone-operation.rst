**To Get Control Tower Landing Zone Operation**

The following ``get-landing-zone-operation`` example get details of an AWS Control Tower landing zone operation::

    aws controltower get-landing-zone-operation \
        --operation-identifier ee9d0d2d-6532-42d8-9b85-3fbb0700a606

Output::

    {
        "operationDetails": {
            "operationIdentifier": "ee9d0d2d-6532-42d8-9b85-3fbb0700a606",
            "operationType": "RESET",
            "startTime": "2025-04-17T03:19:33+00:00",
            "status": "IN_PROGRESS"
        }
    }

For more information, see `AWS Control Tower Getting Started <https://docs.aws.amazon.com/controltower/latest/userguide/getting-started-with-control-tower.html>`__ in the *AWS Control Tower User Guide*.
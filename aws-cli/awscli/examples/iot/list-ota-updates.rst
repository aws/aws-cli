**To list OTA Updates for the account**

The following ``list-ota-updates`` example lists the available OTA updates. ::

    aws iot list-ota-updates

Output::

    {
        "otaUpdates": [
            {
                "otaUpdateId": "itsaupdate",
                "otaUpdateArn": "arn:aws:iot:us-west-2:123456789012:otaupdate/itsaupdate",
                "creationDate": 1557863215.995
            }
        ]
    }

For more information, see `FreeRTOS Over-the-Air Updates <https://docs.aws.amazon.com/freertos/latest/userguide/freertos-ota-dev.html>`__ in the *FreeRTOS User Guide*.

**To list the streams in the account**

The following ``list-streams`` example lists all of the streams in your AWS account. ::

    aws iot list-streams

Output::

    {
        "streams": [
            {
                "streamId": "stream12345",
                "streamArn": "arn:aws:iot:us-west-2:123456789012:stream/stream12345",
                "streamVersion": 1,
                "description": "This stream is used for Amazon FreeRTOS OTA Update 12345."
            },
            {
                "streamId": "stream54321",
                "streamArn": "arn:aws:iot:us-west-2:123456789012:stream/stream54321",
                "streamVersion": 1,
                "description": "This stream is used for Amazon FreeRTOS OTA Update 54321."
            }
        ]
    }

For more information, see `MQTT-based file delivery <https://docs.aws.amazon.com/iot/latest/developerguide/mqtt-based-file-delivery.html>`__ in the *AWS IoT Core Developer Guide*.

**To create a subscription definition**

The following ``create-subscription-definition`` example creates a subscription definition and specifies its initial version. The initial version contains three subscriptions: one for the MQTT topic to which the connector subscribes, one to allow a function to receive temperature readings from AWS IoT, and one to allow AWS IoT to receive status information from the connector. The example provides the ARN for the Lambda function alias that was created earlier by using Lambda's ``create-alias`` command. ::

    aws greengrass create-subscription-definition \
        --initial-version "{\"Subscriptions\": [{\"Id\": \"TriggerNotification\", \"Source\": \"arn:aws:lambda:us-west-2:123456789012:function:TempMonitor:GG_TempMonitor\", \"Subject\": \"twilio/txt\", \"Target\": \"arn:aws:greengrass:us-west-2::/connectors/TwilioNotifications/versions/1\"},{\"Id\": \"TemperatureInput\", \"Source\": \"cloud\", \"Subject\": \"temperature/input\", \"Target\": \"arn:aws:lambda:us-west-2:123456789012:function:TempMonitor:GG_TempMonitor\"},{\"Id\": \"OutputStatus\", \"Source\": \"arn:aws:greengrass:us-west-2::/connectors/TwilioNotifications/versions/1\", \"Subject\": \"twilio/message/status\", \"Target\": \"cloud\"}]}"

Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/subscriptions/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "CreationTimestamp": "2019-06-19T22:34:26.677Z",
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "LastUpdatedTimestamp": "2019-06-19T22:34:26.677Z",
        "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/subscriptions/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Getting started with Greengrass connectors (CLI) <https://docs.aws.amazon.com/greengrass/v1/developerguide/connectors-cli.html>`__ in the *AWS IoT Greengrass Developer Guide*.

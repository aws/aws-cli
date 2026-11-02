**To list the current logging options**

The following ``get-v2-logging-options`` example lists the current logging options for AWS IoT. ::

    aws iot get-v2-logging-options

Output::

    {
        "roleArn": "arn:aws:iam::123456789012:role/service-role/iotLoggingRole",
        "defaultLogLevel": "WARN",
        "disableAllLogs": false
    }

For more information, see `Configure AWS IoT logging <https://docs.aws.amazon.com/iot/latest/developerguide/configure-logging.html>`__ in the *AWS IoT Core Developer Guide*.

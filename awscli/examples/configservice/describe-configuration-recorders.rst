**To get details about the configuration recorder**

The following ``describe-configuration-recorders`` example returns details about the default configuration recorder. ::

    aws configservice describe-configuration-recorders

Output::

    {
        "ConfigurationRecorders": [
            {
                "recordingGroup": {
                    "allSupported": true,
                    "resourceTypes": [],
                    "includeGlobalResourceTypes": true
                },
                "roleARN": "arn:aws:iam::123456789012:role/config-ConfigRole-A1B2C3D4E5F6",
                "name": "default"
            }
        ]
    }

For more information, see `Working with the configuration recorder <https://docs.aws.amazon.com/config/latest/developerguide/stop-start-recorder.html>`__ in the *AWS Config Developer Guide*.

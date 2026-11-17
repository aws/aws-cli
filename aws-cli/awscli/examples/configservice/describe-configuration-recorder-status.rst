**To get status information for the configuration recorder**

The following ``describe-configuration-recorder-status`` example returns the status of the default configuration recorder. ::

    aws configservice describe-configuration-recorder-status

Output::

    {
        "ConfigurationRecordersStatus": [
            {
                "name": "default",
                "lastStatus": "SUCCESS",
                "recording": true,
                "lastStatusChangeTime": 1452193834.344,
                "lastStartTime": 1441039997.819,
                "lastStopTime": 1441039992.835
            }
        ]
    }

For more information, see `Working with the configuration recorder <https://docs.aws.amazon.com/config/latest/developerguide/stop-start-recorder.html>`__ in the *AWS Config Developer Guide*.

**To update the status of a job execution**

The following ``update-job-execution`` example updates the status of the specified job and thing. ::

    aws iot-jobs-data update-job-execution \
        --job-id SampleJob \
        --thing-name MotionSensor1 \
        --status REMOVED

This command produces no output.
Output::

    {
        "executionState": { 
            "status": "REMOVED",
            "versionNumber": 3
        },
    }

For more information, see `Devices and Jobs <https://docs.aws.amazon.com/iot/latest/developerguide/jobs-devices.html>`__ in the *AWS IoT Developer Guide*.

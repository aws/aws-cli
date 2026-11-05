**To check a drift detection operation's status**

The following ``describe-stack-drift-detection-status`` example displays the status of a drift detection operation. Get the by ID running the ``detect-stack-drift`` command. ::

    aws cloudformation describe-stack-drift-detection-status \
        --stack-drift-detection-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/my-stack/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "StackDriftDetectionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "StackDriftStatus": "DRIFTED",
        "DetectionStatus": "DETECTION_COMPLETE",
        "DriftedStackResourceCount": 1,
        "Timestamp": "2019-10-02T05:54:30.902Z"
    }

For more information, see `Detect drift on an entire CloudFormation stack <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/detect-drift-stack.html>`__ in the *AWS CloudFormation User Guide*.

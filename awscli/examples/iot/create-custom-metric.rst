**To create a custom metric published by your devices to Device Defender**

The following ``create-custom-metric`` example creates a custom metric that measures battery percentage. ::

    aws iot create-custom-metric \
        --metric-name "batteryPercentage" \
        --metric-type "number" \
        --display-name "Remaining battery percentage." \
        --client-request-token "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "metricName": "batteryPercentage",
        "metricArn": "arn:aws:iot:us-west-2:1234564789012:custommetric/batteryPercentage"
    }

For more information, see `Custom metrics <https://docs.aws.amazon.com/iot/latest/developerguide/dd-detect-custom-metrics.html>`__ in the *AWS IoT Core Developer Guide*.
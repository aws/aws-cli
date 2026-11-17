**To delete a platform application endpoint**

The following ``delete-endpoint`` example deletes the specified platform application endpoint. ::

    aws sns delete-endpoint \
        --endpoint-arn arn:aws:sns:us-west-2:123456789012:endpoint/GCM/MyApplication/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output.

For more information, see `Setting up an Amazon SNS platform endpoint for mobile notifications <https://docs.aws.amazon.com/sns/latest/dg/mobile-platform-endpoint.html>`__ in the *Amazon Simple Notification Service Developer Guide*.

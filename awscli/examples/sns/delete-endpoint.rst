**To delete a platform application endpoint**

The following ``delete-endpoint`` example deletes the specified platform application endpoint. ::

    aws sns delete-endpoint \
        --endpoint-arn arn:aws:sns:us-west-2:123456789012:endpoint/GCM/MyApplication/12345678-abcd-9012-efgh-345678901234

This command produces no output.

For more information, see `Setting up an Amazon SNS platform endpoint for mobile notifications <https://docs.aws.amazon.com/sns/latest/dg/mobile-platform-endpoint.html>`__ in the *Amazon Simple Notification Service Developer Guide*.

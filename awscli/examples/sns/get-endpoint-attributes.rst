**To list platform application endpoint attributes**

The following ``get-endpoint-attributes`` example lists the attributes for the specified platform application endpoint. ::

    aws sns get-endpoint-attributes \
        --endpoint-arn arn:aws:sns:us-west-2:123456789012:endpoint/GCM/MyApplication/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "Attributes": {
            "Enabled": "true",
            "Token": "EXAMPLE12345..."
        }
    }

For more information, see `Setting up an Amazon SNS platform endpoint for mobile notifications <https://docs.aws.amazon.com/sns/latest/dg/mobile-platform-endpoint.html>`__ in the *Amazon Simple Notification Service Developer Guide*.

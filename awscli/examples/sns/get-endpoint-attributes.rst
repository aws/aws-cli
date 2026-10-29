**To list platform application endpoint attributes**

The following ``get-endpoint-attributes`` example lists the attributes for the specified platform application endpoint. ::

    aws sns get-endpoint-attributes \
        --endpoint-arn arn:aws:sns:us-west-2:123456789012:endpoint/GCM/MyApplication/12345678-abcd-9012-efgh-345678901234

Output::

    {
        "Attributes": {
            "Enabled": "true",
            "Token": "EXAMPLE12345..."
        }
    }

For more information, see `Setting up an Amazon SNS platform endpoint for mobile notifications <https://docs.aws.amazon.com/sns/latest/dg/mobile-platform-endpoint.html>`__ in the *Amazon Simple Notification Service Developer Guide*.

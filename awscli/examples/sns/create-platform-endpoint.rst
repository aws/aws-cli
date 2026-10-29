**To create a platform application endpoint**

The following ``create-platform-endpoint`` example creates an endpoint for the specified platform application using the specified token. ::

    aws sns create-platform-endpoint \
        --platform-application-arn arn:aws:sns:us-west-2:123456789012:app/GCM/MyApplication \
        --token EXAMPLE12345...

Output::

    {
        "EndpointArn": "arn:aws:sns:us-west-2:1234567890:endpoint/GCM/MyApplication/12345678-abcd-9012-efgh-345678901234"
    }

For more information, see `Setting up an Amazon SNS platform endpoint for mobile notifications <https://docs.aws.amazon.com/sns/latest/dg/mobile-platform-endpoint.html>`__ in the *Amazon Simple Notification Service Developer Guide*.

**To get a topic rule destination**

The following ``get-topic-rule-destination`` example gets information about a topic rule destination. ::

    aws iot get-topic-rule-destination \
        --arn "arn:aws:iot:us-west-2:123456789012:ruledestination/http/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "topicRuleDestination": {
            "arn": "arn:aws:iot:us-west-2:123456789012:ruledestination/http/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "status": "DISABLED",
            "httpUrlProperties": {
                "confirmationUrl": "https://example.com"
            }
        }
    }

For more information, see `HTTP action destinations <https://docs.aws.amazon.com/iot/latest/developerguide/http-action-destination.html>`__ in the *AWS IoT Developer Guide*.
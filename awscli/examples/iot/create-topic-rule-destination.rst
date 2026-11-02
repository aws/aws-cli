**To create a topic rule destination**

The following ``create-topic-rule-destination`` example creates a topic rule destination for an HTTP endpoint. ::

    aws iot create-topic-rule-destination \
        --destination-configuration httpUrlConfiguration={confirmationUrl=https://example.com}

Output::

    {
        "topicRuleDestination": {
            "arn": "arn:aws:iot:us-west-2:123456789012:ruledestination/http/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "status": "IN_PROGRESS",
            "statusReason": "Awaiting confirmation. Confirmation message sent on 2020-07-09T22:47:54.154Z; no response received from the endpoint.",
            "httpUrlProperties": {
                "confirmationUrl": "https://example.com"
            }
        }
    }

For more information, see `Creating HTTP action destinations <https://docs.aws.amazon.com/iot/latest/developerguide/http-action-destination.html#http-action-destination-creating>`__ in the *AWS IoT Developer Guide*.
**Example 1: To enable a topic rule destination**

The following ``update-topic-rule-destination`` example enables traffic to a topic rule destination. ::

    aws iot update-topic-rule-destination \
        --arn "arn:aws:iot:us-west-2:123456789012:ruledestination/http/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --status ENABLED

This command produces no output.

For more information, see `Confirming HTTP action destinations <https://docs.aws.amazon.com/iot/latest/developerguide/http-action-destination.html#http-action-destination-confirming>`__ in the *AWS IoT Developer Guide*.

**Example 2: To disable a topic rule destination**

The following ``update-topic-rule-destination`` example disables traffic to a topic rule destination. ::

    aws iot update-topic-rule-destination \
        --arn "arn:aws:iot:us-west-2:123456789012:ruledestination/http/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --status DISABLED

This command produces no output.

For more information, see `Disabling and deleting an HTTP action destination <https://docs.aws.amazon.com/iot/latest/developerguide/http-action-destination.html#http-action-destination-deleting>`__ in the *AWS IoT Developer Guide*.

**Example 3: To send a new confirmation message**

The following ``update-topic-rule-destination`` example sends a new confirmation message for a topic rule destination. ::

    aws iot update-topic-rule-destination \
        --arn "arn:aws:iot:us-west-2:123456789012:ruledestination/http/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --status IN_PROGRESS

This command produces no output.

For more information, see `Sending a new confirmation request <https://docs.aws.amazon.com/iot/latest/developerguide/http-action-destination.html#trigger-confirm>`__ in the *AWS IoT Developer Guide*.
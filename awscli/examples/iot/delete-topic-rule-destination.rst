**To delete a topic rule destination**

The following ``delete-topic-rule-destination`` example deletes the specified topic rule destination. ::

    aws iot delete-topic-rule-destination \
        --arn "arn:aws:iot:us-west-2:123456789012:ruledestination/http/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

This command produces no output.

For more information, see `Disabling and deleting an HTTP action destination <https://docs.aws.amazon.com/iot/latest/developerguide/http-action-destination.html#http-action-destination-deleting>`__ in the *AWS IoT Developer Guide*.
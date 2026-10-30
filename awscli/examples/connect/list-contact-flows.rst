**To list the contact flows in an instance**

The following ``list-contact-flows`` example lists the contact flows in the specified Amazon Connect instance. ::

    aws connect list-contact-flows \
        --instance-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "ContactFlowSummaryList": [
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/contact-flow/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Name": "Default queue transfer",
                "ContactFlowType": "QUEUE_TRANSFER"
            },
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/contact-flow/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Name": "Default agent hold",
                "ContactFlowType": "AGENT_HOLD"
            },
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/contact-flow/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "Name": "Default customer hold",
                "ContactFlowType": "CUSTOMER_HOLD"
            }
        ]
    }

For more information, see `Create Amazon Connect Contact Flows <https://docs.aws.amazon.com/connect/latest/adminguide/connect-contact-flows.html>`__ in the *Amazon Connect Administrator Guide*.

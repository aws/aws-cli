**To list the queues in an instance**

The following ``list-queues`` example lists the queues in the specified Amazon Connect instance. ::

    aws connect list-queues \
        --instance-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 

Output::

    {
        "QueueSummaryList": [
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/queue/agent/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "QueueType": "AGENT"
            },
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/queue/agent/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "QueueType": "AGENT"
            },
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/queue/agent/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "QueueType": "AGENT"
            },
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/queue/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "Name": "BasicQueue",
                "QueueType": "STANDARD"
            }
        ]
    }

For more information, see `Create a Queue <https://docs.aws.amazon.com/connect/latest/adminguide/create-queue.html>`__ in the *Amazon Connect Administrator Guide*.

**To list the hours of operation in an instance**

The following ``list-hours-of-operations`` example lists the hours of operations for the specified Amazon Connect instance. ::

    aws connect list-hours-of-operations \
        --instance-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 

Output::

    {
        "HoursOfOperationSummaryList": [
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/operating-hours/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Name": "Basic Hours"
            }
        ]
    }

For more information, see `Set the Hours of Operation for a Queue <https://docs.aws.amazon.com/connect/latest/adminguide/set-hours-operation.html>`__ in the *Amazon Connect Administrator Guide*.

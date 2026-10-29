**To list the routing profiles in an instance**

The following ``list-routing-profiles`` example lists the routing profiles in the specified Amazon Connect instance. ::

    aws connect list-routing-profiles \
        --instance-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 

Output::

    {
        "RoutingProfileSummaryList": [
            {
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/routing-profile/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Name": "Basic Routing Profile"
            }
        ]
    }

For more information, see `Create a Routing Profile <https://docs.aws.amazon.com/connect/latest/adminguide/routing-profiles.html>`__ in the *Amazon Connect Administrator Guide*.

**To list Control Tower landing zone operations**

The following ``list-landing-zone-operations`` example lists AWS Control Tower landing zone operations. ::

    aws controltower list-landing-zone-operations

Output::

    {
        "landingZoneOperations": [
            {
                "operationIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "operationType": "RESET",
                "status": "SUCCEEDED"
            },
            {
                "operationIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "operationType": "RESET",
                "status": "SUCCEEDED"
            },
            {
                "operationIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "operationType": "UPDATE",
                "status": "SUCCEEDED"
            },
            {
                "operationIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "operationType": "UPDATE",
                "status": "SUCCEEDED"
            }
        ]
    }

For more information, see `Getting started with AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/userguide/getting-started-with-control-tower.html>`__ in the *AWS Control Tower User Guide*.

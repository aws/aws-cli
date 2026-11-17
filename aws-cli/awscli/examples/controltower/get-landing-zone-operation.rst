**To get a Control Tower landing zone operation**

The following ``get-landing-zone-operation`` example gets details of an AWS Control Tower landing zone operation. ::

    aws controltower get-landing-zone-operation \
        --operation-identifier a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "operationDetails": {
            "operationIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "operationType": "RESET",
            "startTime": "2025-04-17T03:19:33+00:00",
            "status": "IN_PROGRESS"
        }
    }

For more information, see `Getting started with AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/userguide/getting-started-with-control-tower.html>`__ in the *AWS Control Tower User Guide*.

**To describe an asset property**

The following ``describe-asset-property`` example describes a wind farm asset's total generated power property. ::

    aws iotsitewise describe-asset-property \
        --asset-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --property-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "assetId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "assetName": "Wind Farm 1",
        "assetModelId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
        "assetProperty": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "name": "Total Generated Power",
            "notification": {
                "topic": "$aws/sitewise/asset-models/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333/assets/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/properties/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "state": "DISABLED"
            },
            "dataType": "DOUBLE",
            "unit": "kW",
            "type": {
                "metric": {
                    "expression": "sum(power)",
                    "variables": [
                        {
                            "name": "power",
                            "value": {
                                "propertyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                                "hierarchyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555"
                            }
                        }
                    ],
                    "window": {
                        "tumbling": {
                            "interval": "1h"
                        }
                    }
                }
            }
        }
    }

For more information, see `Model industrial assets <https://docs.aws.amazon.com/iot-sitewise/latest/userguide/industrial-asset-models.html>`__ in the *AWS IoT SiteWise User Guide*.
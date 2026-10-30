**To describe an asset**

The following ``describe-asset`` example describes a wind farm asset. ::

    aws iotsitewise describe-asset \
        --asset-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "assetId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "assetArn": "arn:aws:iotsitewise:us-west-2:123456789012:asset/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "assetName": "Wind Farm 1",
        "assetModelId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "assetProperties": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "name": "Region",
                "dataType": "STRING"
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "name": "Total Generated Power",
                "dataType": "DOUBLE",
                "unit": "kW"
            }
        ],
        "assetHierarchies": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "name": "Wind Turbines"
            }
        ],
        "assetCreationDate": 1575672453.0,
        "assetLastUpdateDate": 1575672453.0,
        "assetStatus": {
            "state": "ACTIVE"
        }
    }

For more information, see `Check the status of an asset <https://docs.aws.amazon.com/iot-sitewise/latest/userguide/check-asset-status.html>`__ in the *AWS IoT SiteWise User Guide*.
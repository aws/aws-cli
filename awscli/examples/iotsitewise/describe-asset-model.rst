**To describe an asset model**

The following ``describe-asset-model`` example describes a wind farm asset model. ::

    aws iotsitewise describe-asset-model \
        --asset-model-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "assetModelId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "assetModelArn": "arn:aws:iotsitewise:us-west-2:123456789012:asset-model/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "assetModelName": "Wind Farm Model",
        "assetModelDescription": "Represents a wind farm that comprises many wind turbines",
        "assetModelProperties": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "name": "Total Generated Power",
                "dataType": "DOUBLE",
                "unit": "kW",
                "type": {
                    "metric": {
                        "expression": "sum(power)",
                        "variables": [
                            {
                                "name": "power",
                                "value": {
                                    "propertyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                                    "hierarchyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"
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
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "name": "Region",
                "dataType": "STRING",
                "type": {
                    "attribute": {
                        "defaultValue": " "
                    }
                }
            }
        ],
        "assetModelHierarchies": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "name": "Wind Turbines",
                "childAssetModelId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE66666"
            }
        ],
        "assetModelCreationDate": 1575671284.0,
        "assetModelLastUpdateDate": 1575671988.0,
        "assetModelStatus": {
            "state": "ACTIVE"
        }
    }

For more information, see `Check the status of an asset or component model <https://docs.aws.amazon.com/iot-sitewise/latest/userguide/check-model-status.html>`__ in the *AWS IoT SiteWise User Guide*.
**To update an asset model**

The following ``update-asset-model`` example updates a wind farm asset model's description. This example includes the model's existing IDs and definitions, because ``update-asset-model`` overwrites the existing model with the new model. ::

    aws iotsitewise update-asset-model \
        --cli-input-json file://update-wind-farm-model.json

Contents of ``update-wind-farm-model.json``::

    {
        "assetModelName": "Wind Farm Model",
        "assetModelDescription": "Represents a wind farm that comprises many wind turbines",
        "assetModelProperties": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE88888",
                "name": "Region",
                "dataType": "STRING",
                "type": {
                    "attribute": {}
                }
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE99999",
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
                                    "hierarchyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE77777",
                                    "propertyId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE66666"
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
        ],
        "assetModelHierarchies": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE77777",
                "name": "Wind Turbines",
                "childAssetModelId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            }
        ]
    }

Output::

    {
        "assetModelId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "assetModelStatus": {
            "state": "CREATING"
        }
    }

For more information, see `Updating asset models <https://docs.aws.amazon.com/iot-sitewise/latest/userguide/update-asset-models.html>`__ in the *AWS IoT SiteWise User Guide*.
**To retrieve an asset property's current value**

The following ``get-asset-property-value`` example retrieves a wind turbine asset's current total power. ::

    aws iotsitewise get-asset-property-value \
        --asset-id a1b2c3d4-5678-90ab-cdef-EXAMPLE33333 \
        --property-id a1b2c3d4-5678-90ab-cdef-EXAMPLE66666

Output::

    {
        "propertyValue": {
            "value": {
                "doubleValue": 6890.8677520453875
            },
            "timestamp": {
                "timeInSeconds": 1580853000,
                "offsetInNanos": 0
            },
            "quality": "GOOD"
        }
    }

For more information, see `Querying current asset property values <https://docs.aws.amazon.com/iot-sitewise/latest/userguide/current-values.html>`__ in the *AWS IoT SiteWise User Guide*.
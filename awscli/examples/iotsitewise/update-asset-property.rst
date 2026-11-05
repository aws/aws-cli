**Example 1: To update an asset property's alias**

The following ``update-asset-property`` example updates a wind turbine asset's power property alias. ::

    aws iotsitewise update-asset-property \
        --asset-id a1b2c3d4-5678-90ab-cdef-EXAMPLE33333 \
        --property-id a1b2c3d4-5678-90ab-cdef-EXAMPLE55555 \
        --property-alias "/examplecorp/windfarm/1/turbine/1/power" \
        --property-notification-state DISABLED

This command produces no output.

For more information, see `Update an asset property alias <https://docs.aws.amazon.com/iot-sitewise/latest/userguide/update-data-streams-method.html>`__ in the *AWS IoT SiteWise User Guide*.

**Example 2: To enable asset property notifications**

The following ``update-asset-property`` example enables asset property update notifications for a wind turbine asset's power property. Property value updates are published to the MQTT topic ``$aws/sitewise/asset-models/<assetModelId>/assets/<assetId>/properties/<propertyId>``, where each ID is replaced by the property, asset, and model ID of the asset property. ::

    aws iotsitewise update-asset-property \
        --asset-id a1b2c3d4-5678-90ab-cdef-EXAMPLE33333 \
        --property-id a1b2c3d4-5678-90ab-cdef-EXAMPLE66666 \
        --property-notification-state ENABLED \
        --property-alias "/examplecorp/windfarm/1/turbine/1/power"

This command produces no output.

For more information, see `Interacting with other services <https://docs.aws.amazon.com/iot-sitewise/latest/userguide/interact-with-other-services.html>`__ in the *AWS IoT SiteWise User Guide*.
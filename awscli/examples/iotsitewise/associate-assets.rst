**To associate a child asset to a parent asset**

The following ``associate-assets`` example associates a wind turbine asset to a wind farm asset, where the wind turbine asset model exists as a hierarchy in the wind farm asset model. ::

    aws iotsitewise associate-assets \
        --asset-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --hierarchy-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --child-asset-id a1b2c3d4-5678-90ab-cdef-EXAMPLE33333

This command produces no output.

For more information, see `Associating assets <https://docs.aws.amazon.com/iot-sitewise/latest/userguide/add-associated-assets.html>`__ in the *AWS IoT SiteWise User Guide*.
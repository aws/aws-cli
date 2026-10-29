**To disassociate a child asset from a parent asset**

The following ``disassociate-assets`` example disassociates a wind turbine asset from a wind farm asset. ::

    aws iotsitewise disassociate-assets \
        --asset-id a1b2c3d4-5678-90ab-cdef-EXAMPLE44444 \
        --hierarchy-id a1b2c3d4-5678-90ab-cdef-EXAMPLE77777 \
        --child-asset-id a1b2c3d4-5678-90ab-cdef-EXAMPLE33333

This command produces no output.

For more information, see `Associating assets <https://docs.aws.amazon.com/iot-sitewise/latest/userguide/add-associated-assets.html>`__ in the *AWS IoT SiteWise User Guide*.
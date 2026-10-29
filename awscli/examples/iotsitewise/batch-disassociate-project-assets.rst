**To disassociate an asset from a project**

The following ``batch-disassociate-project-assets`` example disassociates a wind farm asset from a project. ::

    aws iotsitewise batch-disassociate-project-assets \
        --project-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --asset-ids a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

This command produces no output.

For more information, see `Adding assets to projects <https://docs.aws.amazon.com/iot-sitewise/latest/appguide/add-assets-to-projects-sd.html>`__ in the *AWS IoT SiteWise Monitor Application Guide*.
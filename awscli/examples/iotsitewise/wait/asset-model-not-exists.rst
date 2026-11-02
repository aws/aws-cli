**To wait for an asset model to not exist**

The following ``wait asset-model-not-exists`` example pauses and resumes only after it can confirm that the specified asset model doesn't exist. ::

    aws iotsitewise wait asset-model-not-exists \
        --asset-model-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output.

For more information, see `Deleting asset models <https://docs.aws.amazon.com/iot-sitewise/latest/userguide/delete-asset-models.html>`__ in the *AWS IoT SiteWise User Guide*.
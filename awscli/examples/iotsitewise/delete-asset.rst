**To delete an asset**

The following ``delete-asset`` example deletes a wind turbine asset. ::

    aws iotsitewise delete-asset \
        --asset-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "assetStatus": {
            "state": "DELETING"
        }
    }

For more information, see `Deleting assets <https://docs.aws.amazon.com/iot-sitewise/latest/userguide/delete-assets.html>`__ in the *AWS IoT SiteWise User Guide*.
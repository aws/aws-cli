**Example 1: To copy an image set without a destination.**

The following ``copy-image-set`` code example makes a duplicate copy of an image set without a destination. ::

    aws medical-imaging copy-image-set \
        --datastore-id 12345678901234567890123456789012 \
        --source-image-set-id ea92b0d8838c72a3f25d00d13616f87e \
        --copy-image-set-information '{"sourceImageSet": {"latestVersionId": "1" } }'



Output::

    {
        "destinationImageSetProperties": {
            "latestVersionId": "2",
            "imageSetWorkflowStatus": "COPYING",
            "updatedAt": 1680042357.432,
            "imageSetId": "b9a06fef182a5f992842f77f8e0868e5",
            "imageSetState": "LOCKED",
            "createdAt": 1680042357.432
        },
        "sourceImageSetProperties": {
            "latestVersionId": "1",
            "imageSetWorkflowStatus": "COPYING_WITH_READ_ONLY_ACCESS",
            "updatedAt": 1680042357.432,
            "imageSetId": "ea92b0d8838c72a3f25d00d13616f87e",
            "imageSetState": "LOCKED",
            "createdAt": 1680027126.436
        },
        "datastoreId": "12345678901234567890123456789012"
    }

**Example 2: To copy an image set with a destination.**

The following ``copy-image-set`` code example makes a duplicate copy of an image set with a destination. ::

    aws medical-imaging copy-image-set \
        --datastore-id 12345678901234567890123456789012 \
        --source-image-set-id ea92b0d8838c72a3f25d00d13616f87e \
        --copy-image-set-information '{"sourceImageSet": {"latestVersionId": "1" }, "destinationImageSet": { "imageSetId": "b9a06fef182a5f992842f77f8e0868e5", "latestVersionId": "1"} }'




Output::

    {
        "destinationImageSetProperties": {
            "latestVersionId": "2",
            "imageSetWorkflowStatus": "COPYING",
            "updatedAt": 1680042505.135,
            "imageSetId": "b9a06fef182a5f992842f77f8e0868e5",
            "imageSetState": "LOCKED",
            "createdAt": 1680042357.432
        },
        "sourceImageSetProperties": {
            "latestVersionId": "1",
            "imageSetWorkflowStatus": "COPYING_WITH_READ_ONLY_ACCESS",
            "updatedAt": 1680042505.135,
            "imageSetId": "ea92b0d8838c72a3f25d00d13616f87e",
            "imageSetState": "LOCKED",
            "createdAt": 1680027126.436
        },
        "datastoreId": "12345678901234567890123456789012"
    }

For more information, see `Copying an image set <https://docs.aws.amazon.com/healthimaging/latest/devguide/copy-image-set.html>`__ in the *AWS HealthImaging Developer Guide*.

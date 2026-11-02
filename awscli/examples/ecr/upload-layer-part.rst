**To upload a layer part**

The following ``upload-layer-part`` example uploads an image layer part to the ``layer-test`` repository. ::

    aws ecr upload-layer-part \
        --repository-name layer-test \
        --upload-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --part-first-byte 0 \
        --part-last-byte 8323314 \
        --layer-part-blob fileb:///var/lib/docker/image/overlay2/layerdb/sha256/ff986b10a018b48074e6d3a68b39aad8ccc002cdad912d4148c0f92b3729323e/layer.b64
  
Output::

    {
        "uploadId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "registryId": "123456789012",
        "lastByteReceived": 8323314,
        "repositoryName": "layer-test"
    }

For more information, see `Pushing an image to an Amazon ECR private repository <https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-push.html>`__ in the *Amazon ECR User Guide*.

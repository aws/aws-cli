**To complete an image layer upload**

The following ``complete-layer-upload`` example completes an image layer upload to the ``layer-test`` repository. ::

    aws ecr complete-layer-upload \
        --repository-name layer-test \
        --upload-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --layer-digests a1b2c3d4-5678-90ab-cdef-EXAMPLE11111:48074e6d3a68b39aad8ccc002cdad912d4148c0f92b3729323e
  
Output::

    {
        "uploadId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "layerDigest": "sha256:9a77f85878aa1906f2020a0ecdf7a7e962d57e882250acd773383224b3fe9a02",
        "repositoryName": "layer-test",
        "registryId": "123456789012"
    }

For more information, see `Pushing an image to an Amazon ECR private repository <https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-push.html>`__ in the *Amazon ECR User Guide*.

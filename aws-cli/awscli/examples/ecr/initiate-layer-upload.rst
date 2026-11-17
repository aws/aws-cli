**To initiate an image layer upload**

The following ``initiate-layer-upload`` example initiates an image layer upload to the ``layer-test`` repository. ::

    aws ecr initiate-layer-upload \
        --repository-name layer-test
  
Output::

    {
        "partSize": 10485760,
        "uploadId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Pushing an image to an Amazon ECR private repository <https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-push.html>`__ in the *Amazon ECR User Guide*.

**To get the download URL of a layer**

The following ``get-download-url-for-layer`` example displays the download URL of a layer with the digest ``sha256:6171c7451a50945f8ddd72f7732cc04d7a0d1f48138a426b2e64387fdeb834ed`` in the ``cluster-autoscaler`` repository. ::

    aws ecr get-download-url-for-layer \
        --repository-name cluster-autoscaler  \
        --layer-digest sha256:6171c7451a50945f8ddd72f7732cc04d7a0d1f48138a426b2e64387fdeb834ed

Output::

    {
        "downloadUrl": "https://prod-us-west-2-starport-layer-bucket.s3.us-west-2.amazonaws.com/e501-123456789012-a1b2c3d4-5678-90ab-cdef-EXAMPLE22222/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20190814T220617Z&X-Amz-SignedHeaders=host&X-Amz-Expires=3600&X-Amz-Credential=AKIA32P3D2JDNMVAJLGF%2F20190814%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Signature=9161345894947a1672467a0da7a1550f2f7157318312fe4941b59976239c3337",
        "layerDigest": "sha256:6171c7451a50945f8ddd72f7732cc04d7a0d1f48138a426b2e64387fdeb834ed"
    }

For more information, see `Pulling an image to your local environment from an Amazon ECR private repository <https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-pull-ecr-image.html>`__ in the *Amazon ECR User Guide*.

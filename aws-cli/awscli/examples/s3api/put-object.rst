**Example 1: To upload an object to Amazon S3**

The following ``put-object`` example uploads an object to Amazon S3. ::

    aws s3api put-object \
        --bucket amzn-s3-demo-bucket \
        --key my-dir/MySampleImage.png \
        --body MySampleImage.png

Output::

    {
        "ETag": "\"6805f2cfc46c0f04559748bb039d69ae\"",
        "ChecksumCRC64NVME": "Kd3SA7ZjkPE=",
        "ChecksumType": "FULL_OBJECT",
        "ServerSideEncryption": "AES256"
    }

For more information, see `Uploading objects <https://docs.aws.amazon.com/AmazonS3/latest/userguide/upload-objects.html>`__ in the *Amazon S3 User Guide*.

**Example 2: To upload a video file to Amazon S3**

The following ``put-object`` example uploads a video file. ::

    aws s3api put-object \
        --bucket amzn-s3-demo-bucket \
        --key my-dir/big-video-file.mp4 \
        --body /media/videos/f-sharp-3-data-services.mp4

Output::

    {
        "ETag": "\"9c8b9f2a5e4d3c2b1a0f9e8d7c6b5a49\"",
        "ChecksumCRC64NVME": "bS5l2pLqN0A=",
        "ChecksumType": "FULL_OBJECT",
        "ServerSideEncryption": "AES256"
    }

For more information, see `Uploading objects <https://docs.aws.amazon.com/AmazonS3/latest/userguide/upload-objects.html>`__ in the *Amazon S3 User Guide*.

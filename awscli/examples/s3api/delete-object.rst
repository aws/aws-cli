**To delete an object**

The following ``delete-object`` example deletes an object named ``test.txt`` from a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api delete-object \
        --bucket amzn-s3-demo-bucket \
        --key test.txt

If bucket versioning is enabled, the output contains the version ID of the delete marker.

Output::

    {
        "VersionId": "9_gKg5vG56F.TTEUdwkxGpJ3tNDlWlGq",
        "DeleteMarker": true
    }

For more information, see `Deleting a single object <https://docs.aws.amazon.com/AmazonS3/latest/userguide/delete-objects.html>`__ in the *Amazon S3 User Guide*.

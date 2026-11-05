**To delete an object by using a JSON file**

The following ``delete-objects`` example deletes an object from a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api delete-objects \
        --bucket amzn-s3-demo-bucket \
        --delete file://delete.json

The file ``delete.json`` is a JSON document in the current directory that specifies the object to delete.

Contents of ``delete.json``::

    {
        "Objects": [
            {
                "Key": "test1.txt"
            }
        ],
        "Quiet": false
    }

Output::

    {
        "Deleted": [
            {
                "DeleteMarkerVersionId": "mYAT5Mc6F7aeUL8SS7FAAqUPO1koHwzU",
                "Key": "test1.txt",
                "DeleteMarker": true
            }
        ]
    }

For more information, see `Deleting multiple objects <https://docs.aws.amazon.com/AmazonS3/latest/userguide/delete-multiple-objects.html>`__ in the *Amazon S3 User Guide*.

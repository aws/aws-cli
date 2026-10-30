**To delete the tag sets of an object**

The following ``delete-object-tagging`` example deletes the tag with the specified key from the object ``doc1.rtf``. ::

    aws s3api delete-object-tagging \
        --bucket amzn-s3-demo-bucket \
        --key doc1.rtf

This command produces no output.

For more information, see `Tagging your objects <https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-tagging.html>`__ in the *Amazon S3 User Guide*.

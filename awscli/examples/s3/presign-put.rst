**Example 1: To create a pre-signed URL with the default one hour lifetime that allows uploading to an object in an S3 bucket**

The following ``presign-put`` command generates a pre-signed URL for a specified bucket and key that is valid for one hour. ::

    aws s3 presign-put s3://DOC-EXAMPLE-BUCKET/test2.txt

Output::

    https://DOC-EXAMPLE-BUCKET.s3.us-west-2.amazonaws.com/key?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAEXAMPLE123456789%2F20210621%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20210621T041609Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=EXAMBLE1234494d5fba3fed607f98018e1dfc62e2529ae96d844123456

**Example 2: To create a pre-signed URL with a custom lifetime that allows uploading to an object in an S3 bucket**

The following ``presign-put`` command generates a pre-signed URL for a specified bucket and key that is valid for one week. ::

    aws s3 presign-put s3://DOC-EXAMPLE-BUCKET/test2.txt \
        --expires-in 604800

Output::

    https://DOC-EXAMPLE-BUCKET.s3.us-west-2.amazonaws.com/key?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAEXAMPLE123456789%2F20210621%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20210621T041609Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=EXAMBLE1234494d5fba3fed607f98018e1dfc62e2529ae96d844123456

For more information, see `Allow Others to Upload an Object <https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html>`__ in the *S3 Developer Guide* guide.

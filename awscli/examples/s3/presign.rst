**To create a pre-signed URL with the default one hour lifetime that links to an object in an S3 bucket**

The following ``presign`` command generates a pre-signed URL for a specified bucket and key that is valid for one hour::

    aws s3 presign s3://awsexamplebucket/test2.txt

Output::

    https://awsexamplebucket.s3.amazonaws.com/test2.txt?AWSAccessKeyId=AKIAEXAMPLEACCESSKEY&Signature=EXHCcBe%EXAMPLEKnz3r8O0AgEXAMPLE&Expires=1555531131

**To create a pre-signed URL with a custom lifetime that links to an object in an S3 bucket**

The following ``presign`` command generates a pre-signed URL for a specified bucket and key that is valid for one week::

    aws s3 presign s3://awsexamplebucket/test2.txt --expires-in 604800

Output::

    https://examplebucket.s3.amazonaws.com/test2.txt?AWSAccessKeyId=AKIAEXAMPLEACCESSKEY&Signature=EXHCcBe%EXAMPLEKnz3r8O0AgEXAMPLE&Expires=1556132848

For more information, see `Share an Object with Others`_ in the *S3 Developer Guide* guide.

.. _`Share an Object with Others`: https://docs.aws.amazon.com/AmazonS3/latest/dev/ShareObjectPreSignedURL.html
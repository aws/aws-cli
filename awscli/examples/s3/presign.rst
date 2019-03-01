**Generating URL to retrieve object using default values**

The following ``presign`` command generates a pre-signed URL for 
a key in a specified bucket to retrieve with default expiration time 
of 3600s::
    
    aws s3 presign s3://mybucket/test2.txt

Output::

    https://mybucket.s3.amazonaws.com/.txt?Signature=abc%3D&Expires=1471536728&AWSAccessKeyId=ABC


**Generating URL to retrieve object with expiration URL**

The following ``presign`` command generates a pre-signed URL for 
a key in a specified bucket to retrieve with number of seconds 
until the pre-signed URL expires::

    aws s3 presign --client-method get_object s3://mybucket/test2.txt --expires-in 1800

Output::

    https://mybucket.s3.amazonaws.com/.txt?Signature=abc%3D&Expires=1471536728&AWSAccessKeyId=ABC


**Generating URL to upload object to bucket**

The following ``presign`` command generates a pre-signed URL to 
upload an object to a specified bucket and key::

    aws s3 presign --client-method put_object s3://mybucket/test2.txt

Output::

    https://mybucket.s3.amazonaws.com/test2.txt?Signature=abc%3D&Expires=1471536728&AWSAccessKeyId=ABC


**Generating URL to upload object with expiration URL**

The following ``presign`` command generates a pre-signed URL to
upload an object to a specified bucket with number of seconds 
until the pre-signed URL expires::

    aws s3 presign --client-method put_object s3://mybucket/test2.txt --expires-in 1800

Output::

    https://mybucket.s3.amazonaws.com/test2.txt?Signature=abc%3D&Expires=1471536728&AWSAccessKeyId=ABC


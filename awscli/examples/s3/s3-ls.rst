1) The following ``ls`` command lists all of the bucket owned by the user.
In this example, the user owns the buckets ``mybucket`` and ``mybucket2``.
The ``CreationTime`` is arbitrary.  Note if ``s3://`` is used for the path
argument ``<S3Path>``, it will list all of the buckets as well.
::

    aws s3 ls

*Output:*
::

           CreationTime Bucket
           ------------ ------
    2013-07-11 17:08:50 mybucket
    2013-07-24 14:55:44 mybucket2 


2) The following ``ls`` command lists objects and common prefixes under
a spcified bucket and prefix.  In this example, the user owns the bucket
``mybucket`` with the objects ``test.txt`` and ``somePrefix/test.txt``.
The ``LastWriteTime`` and ``Length`` are arbitrary.
::

    aws s3 ls s3://mybucket

*Output:*
::
    
    Bucket: mybucket
    Prefix:

          LastWriteTime     Length Name
          -------------     ------ ----
                               PRE somePrefix/
    2013-07-25 17:06:27         88 test.txt


3) The following ``ls`` command lists objects and common prefixes under a
specified bucket and prefix.  However, there are no objects nor common
prefixes under the specified bucket and prefix.
::

    aws s3 ls s3://mybucket/noExistPrefix

*Output:*
::
    
    Bucket: mybucket
    Prefix: noExistPrefix/

          LastWriteTime     Length Name
          -------------     ------ ----


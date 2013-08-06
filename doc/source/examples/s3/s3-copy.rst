1) The following ``copy`` command copies a single s3 object to a specified
bucket and key.
::

    aws s3 copy s3://mybucket/test.txt s3://mybucket/test2.txt

*Output:*
::

    copy: s3://mybucket/test.txt to s3://mybucket/test2.txt

2) The following ``copy`` command copies a single object to a specified
bucket while retaining its original name.
::

    aws s3 copy s3://mybucket/test.txt s3://mybucket2/

*Output:*
::

    copy: s3://mybucket/test.txt to s3://mybucket2/test.txt

3) The following ``copy`` command recursively copies all objects under
a specified prefix and bucket when passed with the parameter
``--recursive``.  In this example, the bucket ``mybucket`` has the
objects ``test1.txt`` and ``test2.txt``.
::

    aws s3 copy s3://mybucket s3://mybucket2 --recursive

*Output:*
::
    
    copy: s3://mybucket/test1.txt to s3://mybucket2/test1.txt
    copy: s3://mybucket/test2.txt to s3://mybucket2/test2.txt

4) The following ``copy`` command recursively copies all objects under
a specifed bucket when passed with the parameter ``--recursive`` while
excluding some objects by using an ``--exclude`` parameter.  In this
example, the bucket ``mybucket`` has the objects ``test1.txt``
and ``test2.jpg``.
::

    aws s3 copy s3://mybucket/ s3://mybucket2/ --recursive --exclude *.jpg

*Output:*
::
    
    copy: s3://mybucket/test1.txt to s3://mybucket2/test1.txt

5) The following ``copy`` command recursively copies all objects under a
specifed bucket when passed with the parameter ``--recursive`` while
excluding all objects under a prefix by using an ``--exclude`` parameter.
In this example, the bucket ``mybucket`` has the objects ``test1.txt``
and ``another/test1.txt``.
::

    aws s3 copy s3://mybucket/ s3://mybucket2/ --recursive --exclude mybucket/another/*

*Output:*
::
    
    copy: s3://mybucket/test1.txt to s3://mybucket2/test1.txt

6) The following ``copy`` command copies a single object to a specified
bucket and key while setting the ACL to ``public-read-write``.
::

    aws s3 copy s3://mybucket/test.txt s3://mybucket/test2.txt --acl public-read-write

*Output:*
::

    copy: s3://mybucket/test.txt to s3://mybucket/test2.txt

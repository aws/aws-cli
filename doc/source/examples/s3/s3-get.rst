1) The following ``get`` command downloads a single object to a specified file locally.
::

    aws s3 get s3://mybucket/test.txt test2.txt 

*Output:*
::

    download: s3://mybucket/test.txt to test2.txt

2) The following ``get`` command downloads a single file to a specified directory locally while retaining its orignal name.
::

    aws s3 get s3://mybucket/test.txt .

*Output:*
::

    download: s3://mybucket/test.txt to test.txt

3) The following ``put`` command recursively downloads all objects under a specified bucket and prefix when passed with the parameter ``--recursive``.  In this example, the bucket ``mybucket`` has the objects ``test1.txt`` and ``test2.txt``.
::

    aws s3 get s3://mybucket . --recursive

*Output:*
::
    
    download: s3://mybucket/test1.txt to test1.txt
    download: s3://mybucket/test2.txt to test2.txt

4) The following ``get`` command recursively downloads all objects under a specified bucket and prefix when passed with the parameter ``--recursive`` while excluding some objects by using an ``--exclude`` parameter.  In this example, the bucket ``mybucket`` has the objects ``test1.txt`` and ``test2.jpg``.
::

    aws s3 get s3://mybucket/ . --recursive --exclude *.jpg

*Output:*
::
    
    download: s3://mybucket/test1.txt to test1.txt

5) The following ``get`` command recursively downloads all objects under a specified bucket and prefix when passed with the parameter ``--recursive`` while excluding all objects under a prefix by using an ``--exclude`` parameter.  In this example, the bucket ``mybucket`` has the objects ``test1.txt`` and ``another/test.txt``.
::

    aws s3 get s3://mybucket/ . --recursive --exclude mybucket/another/*

*Output:*
::
    
    download: s3://mybucket/test1.txt to test1.txt


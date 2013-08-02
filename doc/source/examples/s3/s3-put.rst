1) The following ``put`` command uploads a single file to a specified bucket and key.
::

    aws s3 put test.txt s3://mybucket/test2.txt

*Output:*
::

    upload: test.txt to s3://mybucket/test2.txt

2) The following ``put`` command uploads a single file to a specified bucket while retaining its original name.
::

    aws s3 put test.txt s3://mybucket/

*Output:*
::

    upload: test.txt to s3://mybucket/test.txt

3) The following ``put`` command recursively uploads an entire directory when passed with the parameter ``--recursive``.  In this example, the directory ``myDir`` has the files ``test1.txt`` and ``test2.txt``.
::

    aws s3 put myDir s3://mybucket --recursive

*Output:*
::
    
    upload: myDir/test1.txt to s3://mybucket/test1.txt
    upload: myDir/test2.txt to s3://mybucket/test2.txt

4) The following ``put`` command recursively uploads an entire directory when passed with the parameter ``--recursive`` while excluding some by using an ``--exclude`` parameter.  In this example, the directory ``myDir`` has the files ``test1.txt`` and ``test2.jpg``.
::

    aws s3 put myDir s3://mybucket/ --recursive --exclude *.jpg

*Output:*
::
    
    upload: myDir/test1.txt to s3://mybucket/test1.txt

5) The following ``put`` command recursively uploads an entire directory when passed with the parameter ``--recursive`` while excluding an entire directory by using an ``--exclude`` parameter.  In this example, the directory ``myDir`` has the file ``test1.txt`` and the directory ``anotherDir``.
::

    aws s3 put myDir s3://mybucket/ --recursive --exclude anotherDir/*

*Output:*
::
    
    upload: myDir/test1.txt to s3://mybucket/test1.txt


6) The following ``put`` command uploads a single file to a specified bucket and key while setting the ACL to ``public-read-write``.
::

    aws s3 put test.txt s3://mybucket/test2.txt --acl public-read-write

*Output:*
::

    upload: test.txt to s3://mybucket/test2.txt

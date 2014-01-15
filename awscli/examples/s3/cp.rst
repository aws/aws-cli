1) The following ``cp`` command copies a single file to a specified
bucket and key.
::

    aws s3 cp test.txt s3://mybucket/test2.txt

*Output*::

    upload: test.txt to s3://mybucket/test2.txt

2) The following ``cp`` command copies a single s3 object to a specified
bucket and key.
::

    aws s3 cp s3://mybucket/test.txt s3://mybucket/test2.txt

*Output:*
::

    copy: s3://mybucket/test.txt to s3://mybucket/test2.txt

3) The following ``cp`` command copies a single object to a specified
file locally.
::

    aws s3 cp s3://mybucket/test.txt test2.txt

*Output:*
::

    download: s3://mybucket/test.txt to test2.txt

4) The following ``cp`` command copies a single object to a specified
bucket while retaining its original name.
::

    aws s3 cp s3://mybucket/test.txt s3://mybucket2/

*Output:*
::

    copy: s3://mybucket/test.txt to s3://mybucket2/test.txt

5) When passed with the parameter ``--recursive``, the following ``cp``
command recursively copies all objects under a specified prefix and bucket
to a specified directory.  In this example, the bucket ``mybucket`` has
the objects ``test1.txt`` and ``test2.txt``.
::

    aws s3 cp s3://mybucket . --recursive

*Output:*
::

    download: s3://mybucket/test1.txt to test1.txt
    download: s3://mybucket/test2.txt to test2.txt

6)  When passed with the parameter ``--recursive``, the following ``cp``
command recursively copies all files under a specifed directory to a specified
bucket and prefix while excluding some files by using an ``--exclude``
parameter.  In this example, the directory ``myDir`` has the files
``test1.txt`` and ``test2.jpg``.
::

    aws s3 cp myDir s3://mybucket/ --recursive --exclude "*.jpg"

*Output:*
::

    upload: myDir/test1.txt to s3://mybucket2/test1.txt

7) When passed with the parameter ``--recursive``, the following ``cp``
command recursively copies all objects under a specifed bucket to another
bucket while excluding some objects by using an ``--exclude`` parameter.
In this example, the bucket ``mybucket`` has the objects ``test1.txt``
and ``another/test1.txt``.
::

    aws s3 cp s3://mybucket/ s3://mybucket2/ --recursive --exclude "mybucket/another/*"

*Output:*
::

    copy: s3://mybucket/test1.txt to s3://mybucket2/test1.txt

8) The following ``cp`` command copies a single object to a specified
bucket and key while setting the ACL to ``public-read-write``.
::

    aws s3 cp s3://mybucket/test.txt s3://mybucket/test2.txt --acl public-read-write

*Output:*
::

    copy: s3://mybucket/test.txt to s3://mybucket/test2.txt

9) The following ``cp`` command illustrates the use of the ``--grants``
option to grant read access to all users and full control to a specific user
identified by their email address::

  aws s3 cp file.txt s3://mybucket/ --grants read=uri=http://acs.amazonaws.com/groups/global/AllUsers full=emailaddress=user@example.com

*Output*::

    upload: file.txt to s3://mybucket/file.txt


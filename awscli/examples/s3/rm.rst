The following ``rm`` command deletes a single s3 object::

    aws s3 rm s3://mybucket/test2.txt

Output::

    delete: s3://mybucket/test2.txt

The following ``rm`` command recursively deletes all objects under a specified bucket and prefix when passed with the
parameter ``--recursive``.  In this example, the bucket ``mybucket`` contains the objects ``test1.txt`` and
``test2.txt``::

    aws s3 rm s3://mybucket --recursive

Output::

    delete: s3://mybucket/test1.txt
    delete: s3://mybucket/test2.txt

The following ``rm`` command recursively deletes all objects under a specified bucket and prefix when passed with the
parameter ``--recursive`` while excluding some objects by using an ``--exclude`` parameter.  In this example, the bucket
``mybucket`` has the objects ``test1.txt`` and ``test2.jpg``::

    aws s3 rm s3://mybucket/ --recursive --exclude "*.jpg"

Output::

    delete: myDir/test1.txt to s3://mybucket/test1.txt

The following ``rm`` command recursively deletes all objects under a specified bucket and prefix when passed with the
parameter ``--recursive`` while excluding all objects under a particular prefix by using an ``--exclude`` parameter.  In
this example, the bucket ``mybucket`` has the objects ``test1.txt`` and ``another/test.txt``::

    aws s3 rm s3://mybucket/ --recursive --exclude "mybucket/another/*"

Output::

    delete: myDir/test1.txt to s3://mybucket/test1.txt

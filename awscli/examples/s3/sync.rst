The following ``sync`` command syncs objects under a specified prefix and bucket to files in a local directory by
uploading the local files to s3.  A local file will require uploading if the size of the local file is different than
the size of the s3 object, the last modified time of the local file is newer than the last modified time of the s3
object, or the local file does not exist under the specified bucket and prefix.  In this example, the user syncs the
bucket ``mybucket`` to the local current directory.  The local current directory contains the files ``test.txt`` and
``test2.txt``.  The bucket ``mybucket`` contains no objects::

    aws s3 sync . s3://mybucket

Output::

    upload: test.txt to s3://mybucket/test.txt
    upload: test2.txt to s3://mybucket/test2.txt

The following ``sync`` command syncs objects under a specified prefix and bucket to objects under another specified
prefix and bucket by copying s3 objects.  A s3 object will require copying if the sizes of the two s3 objects differ,
the last modified time of the source is newer than the last modified time of the destination, or the s3 object does not
exist under the specified bucket and prefix destination.  In this example, the user syncs the bucket ``mybucket2`` to
the bucket ``mybucket``.  The bucket ``mybucket`` contains the objects ``test.txt`` and ``test2.txt``.  The bucket
``mybucket2`` contains no objects::

    aws s3 sync s3://mybucket s3://mybucket2

Output::

    copy: s3://mybucket/test.txt to s3://mybucket2/test.txt
    copy: s3://mybucket/test2.txt to s3://mybucket2/test2.txt

The following ``sync`` command syncs files in a local directory to objects under a specified prefix and bucket by
downloading s3 objects.  A s3 object will require downloading if the size of the s3 object differs from the size of the
local file, the last modified time of the s3 object is older than the last modified time of the local file, or the s3
object does not exist in the local directory.  Take note that when objects are downloaded from s3, the last modified
time of the local file is changed to the last modified time of the s3 object.  In this example, the user syncs the
current local directory to the bucket ``mybucket``.  The bucket ``mybucket`` contains the objects ``test.txt`` and
``test2.txt``.  The current local directory has no files::

    aws s3 sync s3://mybucket .

Output::

    download: s3://mybucket/test.txt to test.txt
    download: s3://mybucket/test2.txt to test2.txt

The following ``sync`` command syncs objects under a specified prefix and bucket to files in a local directory by
uploading the local files to s3.  Because the ``--delete`` parameter flag is thrown, any files existing under the
specified prefix and bucket but not existing in the local directory will be deleted.  In this example, the user syncs
the bucket ``mybucket`` to the local current directory.  The local current directory contains the files ``test.txt`` and
``test2.txt``.  The bucket ``mybucket`` contains the object ``test3.txt``::

    aws s3 sync . s3://mybucket --delete

Output::

    upload: test.txt to s3://mybucket/test.txt
    upload: test2.txt to s3://mybucket/test2.txt
    delete: s3://mybucket/test3.txt

The following ``sync`` command syncs objects under a specified prefix and bucket to files in a local directory by
uploading the local files to s3.  Because the ``--exclude`` parameter flag is thrown, all files matching the pattern
existing both in s3 and locally will be excluded from the sync.  In this example, the user syncs the bucket ``mybucket``
to the local current directory.  The local current directory contains the files ``test.jpg`` and ``test2.txt``.  The
bucket ``mybucket`` contains the object ``test.jpg`` of a different size than the local ``test.jpg``::

    aws s3 sync . s3://mybucket --exclude "*.jpg"

Output::

    upload: test2.txt to s3://mybucket/test2.txt

The following ``sync`` command syncs files under a local directory to objects under a specified prefix and bucket by
downloading s3 objects.  This example uses the ``--exclude`` parameter flag to exclude a specified directory
and s3 prefix from the ``sync`` command.  In this example, the user syncs the local current directory to the bucket
``mybucket``.  The local current directory contains the files ``test.txt`` and ``another/test2.txt``.  The bucket
``mybucket`` contains the objects ``another/test5.txt`` and ``test1.txt``::

    aws s3 sync s3://mybucket/ . --exclude "*another/*"

Output::

    download: s3://mybucket/test1.txt to test1.txt

The following ``sync`` command syncs files between two buckets in different regions::

    aws s3 sync s3://my-us-west-2-bucket s3://my-us-east-1-bucket --source-region us-west-2 --region us-east-1
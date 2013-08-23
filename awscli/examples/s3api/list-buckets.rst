**List Your Buckets**

The following example uses the ``list-buckets`` command to display the names of all your Amazon S3 buckets (across all regions).
The example uses jq_ to filter the output of ``list-buckets`` down to only the bucket names.
::

  aws s3api list-buckets | jq ".Buckets[].Name"

For more information about buckets, see `Working with Amazon S3 Buckets`_ in the *Amazon S3 Developer Guide*.

.. _jq: http://stedolan.github.io/jq/
.. _Working with Amazon S3 Buckets: http://docs.aws.amazon.com/AmazonS3/latest/dev/UsingBucket.html

**List the Objects in a Bucket**

The following example uses the ``list-objects`` command to display the names of all the objects in the specified bucket.
The example uses jq_ to filter the output of ``list-objects`` down to the key value and size for each object.
::

  aws s3 list-objects --bucket text-content | jq ".Contents[] | {Key, Size }

For more information about objects, see `Working with Amazon S3 Objects`_ in the *Amazon S3 Developer Guide*.

.. _jq: http://stedolan.github.io/jq/
.. _Working with Amazon S3 Objects: http://docs.aws.amazon.com/AmazonS3/latest/dev/UsingObjects.html

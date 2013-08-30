Delete an object
----------------

The following example uses the ``get-object`` command to download an object from Amazon S3::

  aws s3api delete-object --bucket text-content --key dir-1/my_images.tar.bz2 --region=us-east-1

For more information about deleting objects, see `Deleting Objects`_ in the *Amazon S3 Developer Guide*.

.. _`Deleting Objects`: http://docs.aws.amazon.com/AmazonS3/latest/dev/DeletingObjects.html

Get an object
-------------

The following example uses the ``get-object`` command to download an object from Amazon S3::

  aws s3api get-object --bucket text-content --key dir/my_images.tar.bz2 my_images.tar.bz2

For more information about retrieving objects, see `Getting Objects`_ in the *Amazon S3 Developer Guide*.

.. _`Getting Objects`: http://docs.aws.amazon.com/AmazonS3/latest/dev/GettingObjectsUsingAPIs.html

The following example uses the ``get-object`` command to download an object from Amazon S3::

  aws s3api get-object --bucket text-content --key dir/my_images.tar.bz2 my_images.tar.bz2

Note that the outfile parameter is specified without an option name such as "--outfile". The name of the output file must be the last parameter in the command.

For more information about retrieving objects, see `Getting Objects`_ in the *Amazon S3 Developer Guide*.

.. _`Getting Objects`: http://docs.aws.amazon.com/AmazonS3/latest/dev/GettingObjectsUsingAPIs.html

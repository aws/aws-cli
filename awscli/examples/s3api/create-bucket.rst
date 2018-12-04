The following command creates a bucket named ``my-bucket``::

  aws s3api create-bucket --bucket my-bucket --region us-east-1

Output::

  {
      "Location": "/my-bucket"
  }


The following command creates a bucket named ``my-bucket`` in the
``eu-west-1`` region. Regions outside of ``us-east-1`` require the appropriate
``LocationConstraint`` to be specified in order to create the bucket in the
desired region::

    $ aws s3api create-bucket --bucket my-bucket --region eu-west-1 --create-bucket-configuration LocationConstraint=eu-west-1 


Output::

    {
        "Location": "http://my-bucket.s3.amazonaws.com/"
    }

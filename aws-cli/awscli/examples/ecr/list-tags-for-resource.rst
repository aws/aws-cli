**To list the tags for repository**

The following ``list-tags-for-resource`` example displays a list of the tags associated with the ``hello-world`` repository. ::

    aws ecr list-tags-for-resource \
        --resource-arn arn:aws:ecr:us-west-2:123456789012:repository/hello-world
  
Output::

    {
        "tags": [
            {
                "Key": "Stage",
                "Value": "Integ"
            }
        ]
    }

For more information, see `Tagging a private repository in Amazon ECR <https://docs.aws.amazon.com/AmazonECR/latest/userguide/ecr-using-tags.html>`__ in the *Amazon ECR User Guide*.

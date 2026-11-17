**To tag a repository**

The following ``tag-resource`` example sets a tag with key ``Stage`` and value ``Integ`` on the ``hello-world`` repository. ::

    aws ecr tag-resource \
        --resource-arn arn:aws:ecr:us-west-2:123456789012:repository/hello-world \
        --tags Key=Stage,Value=Integ

This command produces no output.

For more information, see `Tagging a private repository in Amazon ECR <https://docs.aws.amazon.com/AmazonECR/latest/userguide/ecr-using-tags.html>`__ in the *Amazon ECR User Guide*.

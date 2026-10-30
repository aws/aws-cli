**To untag a repository**

The following ``untag-resource`` example removes the tag with the key ``Stage`` from the ``hello-world`` repository. ::

    aws ecr untag-resource \
        --resource-arn arn:aws:ecr:us-west-2:123456789012:repository/hello-world \
        --tag-keys Stage

This command produces no output.

For more information, see `Tagging a private repository in Amazon ECR <https://docs.aws.amazon.com/AmazonECR/latest/userguide/ecr-using-tags.html>`__ in the *Amazon ECR User Guide*.

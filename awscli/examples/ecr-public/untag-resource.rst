**Example 1: To untags an existing public repository in a public registry**

The following ``untag-resource`` example tags a repository named ``project-a/nginx-web-app`` in a public registry. ::

    aws ecr-public untag-resource \
        --resource-arn arn:aws:ecr-public::123456789012:repository/project-a/nginx-web-app \
        --tag-keys stack \
        --region us-west-2

This command produces no output.

For more information, see `Tag an Amazon ECR Public repository <https://docs.aws.amazon.com/AmazonECR/latest/public/ecr-public-using-tags.html>`__ in the *Amazon ECR Public User Guide*.

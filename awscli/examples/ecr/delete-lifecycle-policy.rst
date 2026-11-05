**To delete the lifecycle policy for a repository**

The following ``delete-lifecycle-policy`` example deletes the lifecycle policy for the ``hello-world`` repository. ::

    aws ecr delete-lifecycle-policy \
        --repository-name hello-world

Output::

    {
        "registryId": "123456789012",
        "repositoryName": "hello-world",
        "lifecyclePolicyText": "{\"rules\":[{\"rulePriority\":1,\"description\":\"Remove untagged images.\",\"selection\":{\"tagStatus\":\"untagged\",\"countType\":\"sinceImagePushed\",\"countUnit\":\"days\",\"countNumber\":10},\"action\":{\"type\":\"expire\"}}]}",
        "lastEvaluatedAt": 0.0
    }

For more information, see `Automate the cleanup of images by using lifecycle policies in Amazon ECR <https://docs.aws.amazon.com/AmazonECR/latest/userguide/LifecyclePolicies.html>`__ in the *Amazon ECR User Guide*.

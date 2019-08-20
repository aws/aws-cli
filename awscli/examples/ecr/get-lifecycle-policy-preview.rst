**To retrieve details for a lifecycle policy preview**

The following ``get-lifecycle-policy-preview`` example retrieves the result of a lifecycle policy preview for a repository called ``project-a/amazon-ecs-sample`` in the default registry for an account. ::

    aws ecr get-lifecycle-policy-preview \
        --repository-name "project-a/amazon-ecs-sample"

Output::

    {
        "registryId": "<aws_account_id>",
        "repositoryName": "project-a/amazon-ecs-sample",
        "lifecyclePolicyText": "{\n    \"rules\": [\n        {\n            \"rulePriority\": 1,\n            \"description\": \"Expire images older than 14 days\",\n            \"selection\": {\n                \"tagStatus\": \"untagged\",\n                \"countType\": \"sinceImagePushed\",\n                \"countUnit\": \"days\",\n                \"countNumber\": 14\n            },\n            \"action\": {\n                \"type\": \"expire\"\n            }\n        }\n    ]\n}\n",
        "status": "COMPLETE",
        "previewResults": [],
        "summary": {
            "expiringImageTotalCount": 0
        }
    }

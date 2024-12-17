**Example 1: To creates or updates the catalog data for a repository in a public registry.**

The following ``put-repository-catalog-data`` example creates or update catalog data for reposiotry named `project-a/nginx-web-app` in a public registry, along with logoImageBlob, aboutText, usageText and tags information. ::

    aws ecr-public put-repository-catalog-data \
        --repository-name project-a/nginx-web-app \
        --cli-input-json file://repository-catalog-data.json \
        --region us-east-1

Contents of ``repository-catalog-data.json``::

    {
        "catalogData": {
            "description": "My project-a ECR Public Repository",
            "architectures": [
                "ARM",
                "ARM 64",
                "x86",
                "x86-64"
            ],
            "operatingSystems": [
                "Linux"
            ],
            "logoImageBlob": "iVBORw0KGgoAAAANSUhEUgAAAYYAAAGGCAMAAABIXtbXAAAAq1BMVEVHcEz// <abbreviated>",
            "aboutText": "## Quick reference.",
            "usageText": "## Supported architectures are as follows"
        }
    }

Output::

    {
        "catalogData": {
            "description": "My project-a ECR Public Repository",
            "architectures": [
                "ARM",
                "ARM 64",
                "x86",
                "x86-64"
            ],
            "operatingSystems": [
                "Linux"
            ],
            "logoUrl": "https://d3g9o9u8re44ak.cloudfront.net/logo/491d3846-8f33-4d8b-a10c-c2ce271e6c0d/4f09d87c-2569-4916-a932-5c296bf6f88a.png",
            "aboutText": "## Quick reference.",
            "usageText": "## Supported architectures are as follows."
        }
    }

For more information, see `Repository catalog data <https://docs.aws.amazon.com/AmazonECR/latest/public/public-repository-catalog-data.html>`__ in the *Amazon ECR Public*.

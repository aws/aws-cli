**To create or update the catalog data for a repository in a public registry**

The following ``put-repository-catalog-data`` example creates or update catalog data for reposiotry named `project-a/nginx-web-app` in a public registry, along with logoImageBlob, aboutText, usageText and tags information. ::

    aws ecr-public put-repository-catalog-data \
        --repository-name project-a/nginx-web-app \
        --cli-input-json file://repository-catalog-data.json \
        --region us-east-1

Contents of ``repository-catalog-data.json``::

    {
        "repositoryName": "project-a/nginx-web-app",
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
            "logoImageBlob": "iVBORw0KGgoA<<truncated-for-better-reading>>ErkJggg==",
            "aboutText": "## Quick reference.",
            "usageText": "## Supported architectures are as follows."
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
            "logoUrl": "https://d3g9o9u8re44ak.cloudfront.net/logo/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222.png",
            "aboutText": "## Quick reference.",
            "usageText": "## Supported architectures are as follows."
        }
    }

For more information, see `Specifying the repository catalog data in Amazon ECR public <https://docs.aws.amazon.com/AmazonECR/latest/public/public-repository-catalog-data.html>`__ in the *Amazon ECR Public User Guide*.

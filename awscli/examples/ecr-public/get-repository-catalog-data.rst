**To retrieve catalog metadata for a repository in a public registry**

The following ``get-repository-catalog-data`` example lists the catalog metadata for the repository ``project-a/nginx-web-app`` in a public registry. ::

    aws ecr-public get-repository-catalog-data \
        --repository-name project-a/nginx-web-app \
        --region us-east-1

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
            "aboutText": "## Quick reference\n\nMaintained <truncated>",
            "usageText": "## Supported architectures\n\namd64, arm64v8\n\n## <truncated>"
        }
    }

For more information, see `Specifying the repository catalog data in Amazon ECR public <https://docs.aws.amazon.com/AmazonECR/latest/public/public-repository-catalog-data.html>`__ in the *Amazon ECR Public User Guide*.

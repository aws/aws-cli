**To retrieve catalog metadata for a public ECR registry**

The following ``get-registry-catalog-data`` example retrieves catalog metadata for an ECR public registry. ::

    aws ecr-public get-registry-catalog-data \
        --region us-east-1

Output::

    {
        "registryCatalogData": {
            "displayName": "YourCustomPublicRepositoryalias"
        }
    }

For more information, see `Updating registry settings in Amazon ECR public <https://docs.aws.amazon.com/AmazonECR/latest/public/public-registry-settings.html>`__ in the *Amazon ECR Public User Guide*.

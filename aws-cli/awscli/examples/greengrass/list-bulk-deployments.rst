**To list bulk deployments**

The following ``list-bulk-deployments`` example lists all bulk deployments. ::

    aws greengrass list-bulk-deployments

Output::

    {
        "BulkDeployments": [
            {
                "BulkDeploymentArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/bulk/deployments/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "BulkDeploymentId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "CreatedAt": "2019-06-25T16:11:33.265Z"
            }
        ]
    }

For more information, see `Create bulk deployments for groups <https://docs.aws.amazon.com/greengrass/v1/developerguide/bulk-deploy-cli.html>`__ in the *AWS IoT Greengrass Developer Guide*.

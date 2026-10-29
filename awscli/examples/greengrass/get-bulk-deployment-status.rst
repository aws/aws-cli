**To check the status of your bulk deployment**

The following ``get-bulk-deployment-status`` example retrieves status information for the specified bulk deployment operation. In this example, the file that specified the groups to be deployed has an invalid input record. ::

    aws greengrass get-bulk-deployment-status \
        --bulk-deployment-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "BulkDeploymentMetrics": {
            "InvalidInputRecords": 1,
            "RecordsProcessed": 1,
            "RetryAttempts": 0
        },
        "BulkDeploymentStatus": "Completed",
        "CreatedAt": "2019-06-25T16:11:33.265Z",
        "tags": {}
    }

For more information, see `Create bulk deployments for groups <https://docs.aws.amazon.com/greengrass/v1/developerguide/bulk-deploy-cli.html>`__ in the *AWS IoT Greengrass Developer Guide*.

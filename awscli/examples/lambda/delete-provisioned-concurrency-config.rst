**To delete a provisioned concurrency configuration**

The following ``delete-provisioned-concurrency-config`` example deletes the provisioned concurrency configuration for the ``GREEN`` alias of the specified function. This command produces no output. ::

    aws lambda delete-provisioned-concurrency-config \
        --function-name my-function \
        --qualifier GREEN

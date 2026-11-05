**To update a compute environment**

The following ``update-compute-environment`` example disables the `P2OnDemand` compute environment so it can be deleted. ::

    aws batch update-compute-environment \
        --compute-environment P2OnDemand \
        --state DISABLED

Output::

    {
        "computeEnvironmentName": "P2OnDemand",
        "computeEnvironmentArn": "arn:aws:batch:us-west-2:123456789012:compute-environment/P2OnDemand"
    }

For more information, see `Update a compute environment in AWS Batch <https://docs.aws.amazon.com/batch/latest/userguide/updating-compute-environments.html>`__ in the *AWS Batch User Guide*.

**To update a compute environment**

The following ``update-compute-environment`` example disables the `P2OnDemand` compute environment so it can be deleted. ::

    aws batch update-compute-environment --compute-environment P2OnDemand --state DISABLED

Output::

    {
        "computeEnvironmentName": "P2OnDemand",
        "computeEnvironmentArn": "arn:aws:batch:us-east-1:012345678910:compute-environment/P2OnDemand"
    }

**To describe a compute environment**

The following ``describe-compute-environments`` example describes the `P2OnDemand` compute environment. ::

    aws batch describe-compute-environments \
        --compute-environments P2OnDemand

Output::

    {
        "computeEnvironments": [
            {
                "status": "VALID",
                "serviceRole": "arn:aws:iam::123456789012:role/AWSBatchServiceRole",
                "computeEnvironmentArn": "arn:aws:batch:us-west-2:123456789012:compute-environment/P2OnDemand",
                "computeResources": {
                    "subnets": [
                        "subnet-220c0e0a",
                        "subnet-1a95556d",
                        "subnet-978f6dce"
                    ],
                    "tags": {
                        "Name": "Batch Instance - P2OnDemand"
                    },
                    "desiredvCpus": 48,
                    "minvCpus": 0,
                    "instanceTypes": [
                        "p2"
                    ],
                    "securityGroupIds": [
                        "sg-cf5093b2"
                    ],
                    "instanceRole": "ecsInstanceRole",
                    "maxvCpus": 128,
                    "type": "EC2",
                    "ec2KeyPair": "id_rsa"
                },
                "statusReason": "ComputeEnvironment Healthy",
                "ecsClusterArn": "arn:aws:ecs:us-west-2:123456789012:cluster/P2OnDemand_Batch_2c06f29d-d1fe-3a49-879d-42394c86effc",
                "state": "ENABLED",
                "computeEnvironmentName": "P2OnDemand",
                "type": "MANAGED"
            }
        ]
    }

For more information, see `Compute environments for AWS Batch <https://docs.aws.amazon.com/batch/latest/userguide/compute_environments.html>`__ in the *AWS Batch User Guide*.

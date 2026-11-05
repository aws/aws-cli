**Example 1: To create a managed compute environment with On-Demand instances**

The following ``create-compute-environment`` example creates a managed compute environment with specific C4 instance types that are launched on demand. The compute environment is called `C4OnDemand`. ::

    aws batch create-compute-environment \
        --cli-input-json file://<path_to_json_file>/C4OnDemand.json

Contents of ``C4OnDemand.json``::

    {
        "computeEnvironmentName": "C4OnDemand",
        "type": "MANAGED",
        "state": "ENABLED",
        "computeResources": {
            "type": "EC2",
            "minvCpus": 0,
            "maxvCpus": 128,
            "desiredvCpus": 48,
            "instanceTypes": [
                "c4.large",
                "c4.xlarge",
                "c4.2xlarge",
                "c4.4xlarge",
                "c4.8xlarge"
            ],
            "subnets": [
                "subnet-220c0e0a",
                "subnet-1a95556d",
                "subnet-978f6dce"
            ],
            "securityGroupIds": [
                "sg-cf5093b2"
            ],
            "ec2KeyPair": "id_rsa",
            "instanceRole": "ecsInstanceRole",
            "tags": {
                "Name": "Batch Instance - C4OnDemand"
            }
        },
        "serviceRole": "arn:aws:iam::123456789012:role/AWSBatchServiceRole"
    }

Output::

    {
        "computeEnvironmentName": "C4OnDemand",
        "computeEnvironmentArn": "arn:aws:batch:us-west-2:123456789012:compute-environment/C4OnDemand"
    }

For more information, see `Create a compute environment <https://docs.aws.amazon.com/batch/latest/userguide/create-compute-environment.html>`__ in the *AWS Batch User Guide*.

**Example 2: To create a managed compute environment with Spot Instances**

The following ``create-compute-environment`` example creates a managed compute environment with the M4 instance type that is launched when the Spot bid price is at or below 20% of the On-Demand price for the instance type. The compute environment is called `M4Spot`. ::

    aws batch create-compute-environment \
        --cli-input-json file://<path_to_json_file>/M4Spot.json

Contents of ``M4Spot.json``::

    {
        "computeEnvironmentName": "M4Spot",
        "type": "MANAGED",
        "state": "ENABLED",
        "computeResources": {
            "type": "SPOT",
            "spotIamFleetRole": "arn:aws:iam::123456789012:role/aws-ec2-spot-fleet-role",
            "minvCpus": 0,
            "maxvCpus": 128,
            "desiredvCpus": 4,
            "instanceTypes": [
                "m4"
            ],
            "bidPercentage": 20,
            "subnets": [
                "subnet-220c0e0a",
                "subnet-1a95556d",
                "subnet-978f6dce"
            ],
            "securityGroupIds": [
                "sg-cf5093b2"
            ],
            "ec2KeyPair": "id_rsa",
            "instanceRole": "ecsInstanceRole",
            "tags": {
                "Name": "Batch Instance - M4Spot"
            }
        },
        "serviceRole": "arn:aws:iam::123456789012:role/AWSBatchServiceRole"
    }

Output::

    {
        "computeEnvironmentName": "M4Spot",
        "computeEnvironmentArn": "arn:aws:batch:us-west-2:123456789012:compute-environment/M4Spot"
    }

For more information, see `Create a compute environment <https://docs.aws.amazon.com/batch/latest/userguide/create-compute-environment.html>`__ in the *AWS Batch User Guide*.

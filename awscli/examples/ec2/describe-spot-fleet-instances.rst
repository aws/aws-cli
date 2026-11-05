**To describe the Spot Instances associated with a Spot fleet**

The following ``describe-spot-fleet-instances`` example lists the Spot instances associated with the specified Spot fleet. ::

    aws ec2 describe-spot-fleet-instances \
        --spot-fleet-request-id sfr-73fbd2ce-aa30-494c-8788-1cee4EXAMPLE

Output::

    {
        "ActiveInstances": [
            {
                "InstanceId": "i-1234567890abcdef0",
                "InstanceType": "m3.medium",
                "SpotInstanceRequestId": "sir-08b93456"
            }
        ],
        "SpotFleetRequestId": "sfr-73fbd2ce-aa30-494c-8788-1cee4EXAMPLE"
    }

For more information, see `Describe a Spot Fleet request, its instances, and event history <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/manage-spot-fleet.html>`__ in the *Amazon EC2 User Guide*.

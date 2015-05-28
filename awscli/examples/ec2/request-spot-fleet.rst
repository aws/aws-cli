**To request a Spot fleet in a nondefault VPC**

This example command creates a request for a Spot fleet in a nondefault VPC.

Command::

  aws ec2 request-spot-fleet --spot-fleet-request-config {\"TargetCapacity\":2,\"SpotPrice\":\"0.05\",\"IamFleetRole\":\"arn:aws:iam::123456789012:role/my-spot-fleet-role\",\"LaunchSpecifications\":[{\"ImageId\":\"ami-1a2b3c4d\",\"InstanceType\":\"m3.medium\",\"SubnetId\":\"subnet-a61dafcf\"}]}

Output::

  {
    "SpotFleetRequestId": "sfr-73fbd2ce-aa30-494c-8788-1cee4EXAMPLE"
  }


**To request a Spot fleet in a default VPC or EC2-Classic**

This example command creates a request for a Spot fleet in a default VPC or EC2-Classic.

Command::

  aws ec2 request-spot-fleet --spot-fleet-request-config {\"TargetCapacity\":2,\"SpotPrice\":\"0.05\",\"IamFleetRole\":\"arn:aws:iam::123456789012:role/my-spot-fleet-role\",\"LaunchSpecifications\":[{\"ImageId\":\"ami-1a2b3c4d\",\"InstanceType\":\"m3.medium\",\"Placement\":{\"AvailabilityZone\":\"us-west-2b\"}}]}

Output::

  {
    "SpotFleetRequestId": "sfr-73fbd2ce-aa30-494c-8788-1cee4EXAMPLE"
  }


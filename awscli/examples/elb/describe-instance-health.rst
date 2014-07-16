**To describe the health of a running back-end instance**

This example describes health of a specified instance that is InService.

Command::

  aws elb describe-instance-health --load-balancer-name MyHTTPSLoadBalancer  --instances i-cb439ec2

Output::

  {
    "InstanceStates": [
      {
        "InstanceId": "i-cb439ec2",
        "ReasonCode": "N/A",
        "State": "InService",
        "Description": "N/A"
      }
    ]
  }

**To describe the health of an unhealthy back-end instance**

This example describes health of a specified instance that is OutOfService.

Command::

  aws elb describe-instance-health --load-balancer-name MyHTTPSLoadBalancer  --instances i-42fd1d74

Output::

  {
    "InstanceStates": [
      {
        "InstanceId": "i-cb439ec2",
        "ReasonCode": "N/A",
        "State": "InService",
        "Description": "N/A"
      }
    ]
  }

**To describe the health of an unhealthy back-end instance**

This example describes health of a specified instance that is registering.

Command::

  aws elb describe-instance-health --load-balancer-name MyHTTPSLoadBalancer  --instances i-7299c809

Output::

  {
    "InstanceStates": [
      {
        "InstanceId": "i-7299c809",
        "ReasonCode": "ELB",
        "State": "OutOfService",
        "Description": "Instance registration is still in progress"
      }
    ]
  }


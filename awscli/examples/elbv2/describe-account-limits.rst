**To describe your Elastic Load Balancing limits**

This example describes the Elastic Load Balancing limits for your AWS account.

Command::

  aws elbv2 describe-account-limits

Output::

  {
      "Limits": [
        {
            "Name": "application-load-balancers",
            "Max": "20"
        },
        {
            "Name": "target-groups",
            "Max": "3000"
        },
        {
            "Name": "targets-per-application-load-balancer",
            "Max": "1000"
        },
        {
            "Name": "listeners-per-application-load-balancer",
            "Max": "50"
        },
        {
            "Name": "rules-per-application-load-balancer",
            "Max": "100"
        },
        {
            "Name": "network-load-balancers",
            "Max": "20"
        },
        {
            "Name": "targets-per-network-load-balancer",
            "Max": "200"
        },
        {
            "Name": "listeners-per-network-load-balancer",
            "Max": "50"
        }
    ]
  }

**To get description of the load balancers**

This example describes a specified load balancer.

Command::

  aws elb describe-load-balancers --load-balancer-name MyHTTPSLoadBalancer

Output::

  {
    "LoadBalancerDescriptions": [
      {
        "Subnets": [],
        "CanonicalHostedZoneNameID": "Z3DZXE0Q79N41H",
        "CanonicalHostedZoneName": "MyHTTPSLoadBalancer-12345678.us-east-1.elb.amazonaws.com",
        "ListenerDescriptions": [
          {
            "Listener": {
              "InstancePort": 443,
              "Protocol": "HTTPS",
              "LoadBalancerPort": 443,
              "SSLCertificateId": "arn:aws:iam::012345678901:server-certificate/scert",
              "InstanceProtocol": "HTTPS"
            },
            "PolicyNames": [
              "ELBSecurityPolicy-2014-01"
            ]
          },
          {
            "Listener": {
              "InstancePort": 80,
              "LoadBalancerPort": 80,
              "Protocol": "HTTP",
              "InstanceProtocol": "HTTP"
            },
            "PolicyNames": []
          }
        ],
        "HealthCheck": {
          "HealthyThreshold": 10,
          "Interval": 30,
          "Target": "HTTP:80/",
          "Timeout": 5,
          "UnhealthyThreshold": 2
        },
        "BackendServerDescriptions": [
          {
            "InstancePort": 80,
            "PolicyNames": [
              "EnableProxyProtocol"
            ]
          }
        ],
        "Instances": [],
        "DNSName": "MyHTTPSLoadBalancer-12345678.us-east-1.elb.amazonaws.com",
        "SecurityGroups": [],
        "Policies": {
          "LBCookieStickinessPolicies": [],
          "AppCookieStickinessPolicies": [],
          "OtherPolicies": [
            "AWSConsole-SSLNegotiationPolicy-MyHTTPSLoadBalancer-1395199443332",
            "ELBSecurityPolicy-2014-01",
            "AWSConsole-SSLNegotiationPolicy-MyHTTPSLoadBalancer-1401221052287",
            "EnableProxyProtocol",
            "MySSLNegotiationPolicy"
          ]
        },
        "LoadBalancerName": "MyHTTPSLoadBalancer",
        "CreatedTime": "2014-03-19T03:24:02.650Z",
        "AvailabilityZones": [
          "us-east-1a"
        ],
        "Scheme": "internet-facing",
        "SourceSecurityGroup": {
          "OwnerAlias": "amazon-elb",
          "GroupName": "amazon-elb-sg"
        }
      }
    ]
  }


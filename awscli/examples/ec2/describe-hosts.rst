**To describe Dedicated hosts in your account and generate a machine-readable list**

To output a list of Dedicated host IDs in JSON (comma separated).

Command::

  aws ec2 describe-hosts --query 'Hosts[].HostId' --output json

Output::

  [
  "h-085664df5899941c",
  "h-056c1b0724170dc38"
  ]

To output a list of Dedicated host IDs in plaintext (comma separated).

Command::

  aws ec2 describe-hosts --query 'Hosts[].HostId' --output text

Output::
h-085664df5899941c
h-056c1b0724170dc38

**To describe available Dedicated hosts in your account**

Command::

  aws ec2 describe-hosts --filter "Name=state,Values=available"

Output::

  { 
    "Hosts":  [
        {
            "HostId": "h-085664df5899941c"
            "HostProperties: {
                "Cores": 20,
                 "Sockets": 2,
                  "InstanceType": "m3.medium".
                  "TotalVCpus": 32
             },
             "Instances": [],
              "State": "available",
              "AvailabilityZone": "us-east-1b",
              "AvailableCapacity": {
                  "AvailableInstanceCapacity": [
                      {
                            "AvailableCapacity": 32,
                            "InstanceType": "m3.medium",
                            "TotalCapacity": 32
                      }
                   ],
                   "AvailableVCpus": 32
              },
              "AutoPlacement": "off"
       }
    ]
  }
  

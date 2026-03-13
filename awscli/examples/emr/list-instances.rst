The following command lists all of the instances in a cluster with the cluster ID ``j-3C6XNQ39VR9WL``::

  aws emr list-instances --cluster-id j-3C6XNQ39VR9WL

Output::

  For a uniform instance group based cluster
    {
      "Instances": [
           {
              "Status": {
                  "Timeline": {
                      "ReadyDateTime": "2015-06-01T23:13:20.030+00:00",
                      "CreationDateTime": "2015-06-01T23:06:00.152+00:00"
                  },
                  "State": "RUNNING",
                  "StateChangeReason": {}
              },
              "Ec2InstanceId": "i-f19ecfee",
              "PublicDnsName": "ec2-52-52-41-150.us-west-2.compute.amazonaws.com",
              "PrivateDnsName": "ip-172-21-11-216.us-west-2.compute.internal",
              "PublicIpAddress": "52.52.41.150",
              "Id": "ci-3NNHQUQ2TWB6Y",
              "PrivateIpAddress": "172.21.11.216"
          },
          {
              "Status": {
                  "Timeline": {
                      "ReadyDateTime": "2015-06-01T23:13:20.031+00:00",
                      "CreationDateTime": "2015-06-01T23:05:49.102+00:00"
                  },
                  "State": "RUNNING",
                  "StateChangeReason": {}
              },
              "Ec2InstanceId": "i-1feee4c2",
              "PublicDnsName": "ec2-52-63-246-32.us-west-2.compute.amazonaws.com",
              "PrivateDnsName": "ip-172-31-24-130.us-west-2.compute.internal",
              "PublicIpAddress": "52.63.246.32",
              "Id": "ci-GAOCMKNKDCV7",
              "PrivateIpAddress": "172.21.11.215"
          },
          {
              "Status": {
                  "Timeline": {
                      "ReadyDateTime": "2015-06-01T23:13:20.031+00:00",
                      "CreationDateTime": "2015-06-01T23:05:49.102+00:00"
                  },
                  "State": "RUNNING",
                  "StateChangeReason": {}
              },
              "Ec2InstanceId": "i-15cfeee3",
              "PublicDnsName": "ec2-52-25-246-63.us-west-2.compute.amazonaws.com",
              "PrivateDnsName": "ip-172-31-24-129.us-west-2.compute.internal",
              "PublicIpAddress": "52.25.246.63",
              "Id": "ci-2W3TDFFB47UAD",
              "PrivateIpAddress": "172.21.11.214"
          }
      ]
    }


  For a fleet based cluster:
     {
        "Instances": [
            {
                "Status": {
                    "Timeline": {
                        "ReadyDateTime": "2017-02-23T00:46:50.878+00:00",
                        "CreationDateTime": "2017-02-23T00:43:08.367+00:00",
                        "EndDateTime": "2017-02-25T11:43:10.924+00:00"
                    },
                    "State": "TERMINATED",
                    "StateChangeReason": {
                        "Message": "Instance was terminated."
                    }
                },
                "Ec2InstanceId": "i-xxxxx",
                "InstanceFleetId": "if-xxxxx",
                "EbsVolumes": [],
                "PublicDnsName": "ec2-xx-xxx-xxx-xxx.compute-1.amazonaws.com",
                "InstanceType": "m3.xlarge",
                "PrivateDnsName": "ip-xx-xx-xxx-xx.ec2.internal",
                "Market": "SPOT",
                "PublicIpAddress": "xx.xx.xxx.xxx",
                "Id": "ci-xxxxx",
                "PrivateIpAddress": "10.47.191.80"
            }
        ]
    }

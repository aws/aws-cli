The following command creates a replication instance named ``my-replication-db`` with 5GB of storage::

  aws dms create-replication-instance --replication-instance-identifier my-replication-db --replication-instance-class dms.t2.micro --allocated-storage 5

Output::

  {
    "ReplicationInstance": {
      "PubliclyAccessible": true,
      "ReplicationInstanceArn": "arn:aws:dms:us-east-1:123456789012:rep:6UTDJGBOUS3VI3SUWA66XFJCJQ ",
      "ReplicationInstanceClass": "dms.t2.micro",
      "ReplicationSubnetGroup": {
        "ReplicationSubnetGroupDescription": "default",
        "Subnets": [{
          "SubnetStatus": "Active",
          "SubnetIdentifier": "subnet-f6dd91af",
          "SubnetAvailabilityZone": {
            "Name": "us-east-1d"
          }
        }, {
          "SubnetStatus": "Active",
          "SubnetIdentifier": "subnet-3605751d",
          "SubnetAvailabilityZone": {
            "Name": "us-east-1b"
          }
        }, {
          "SubnetStatus": "Active",
          "SubnetIdentifier": "subnet-c2daefb5",
          "SubnetAvailabilityZone": {
            "Name": "us-east-1c"
          }
        }, {
          "SubnetStatus": "Active",
          "SubnetIdentifier": "subnet-85e90cb8",
          "SubnetAvailabilityZone": {
            "Name": "us-east-1e"
          }
        }],
        "VpcId": "vpc-6741a603",
        "SubnetGroupStatus": "Complete",
        "ReplicationSubnetGroupIdentifier": "default"
      },
      "AutoMinorVersionUpgrade": true,
      "ReplicationInstanceStatus": "creating",
      "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/4c1731d6-5435-ed4d-be13-d53411a7cfbd",
      "AllocatedStorage": 5,
      "EngineVersion": "1.5.0",
      "ReplicationInstanceIdentifier": "test-rep-1",
      "PreferredMaintenanceWindow": "sun:06:00-sun:14:00",
      "PendingModifiedValues": {}
    }
  }

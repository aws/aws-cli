**To describe your network ACLs**

This example describes your network ACLs.

Command::

  aws ec2 describe-network-acls

Output::

  {
      "NetworkAcls": [
          {
              "Associations": [],
              "NetworkAclId": "acl-7aaabd18",
              "VpcId": "vpc-a01106c2",
              "Tags": [],
              "Entries": [
                  {
                      "CidrBlock": "0.0.0.0/0",
                      "RuleNumber": 100,
                      "Protocol": "-1",
                      "Egress": true,
                      "RuleAction": "allow"
                  },
                  {
                      "CidrBlock": "0.0.0.0/0",
                      "RuleNumber": 32767,
                      "Protocol": "-1",
                      "Egress": true,
                      "RuleAction": "deny"
                  },
                  {
                      "CidrBlock": "0.0.0.0/0",
                      "RuleNumber": 100,
                      "Protocol": "-1",
                      "Egress": false,
                      "RuleAction": "allow"
                  },
                  {
                      "CidrBlock": "0.0.0.0/0",
                      "RuleNumber": 32767,
                      "Protocol": "-1",
                      "Egress": false,
                      "RuleAction": "deny"
                  }
              ],
              "IsDefault": true
          },  
          {
              "Associations": [],
              "NetworkAclId": "acl-5fb85d36",
              "VpcId": "vpc-a01106c2",
              "Tags": [],
              "Entries": [
                  {
                      "CidrBlock": "0.0.0.0/0",
                      "RuleNumber": 32767,
                      "Protocol": "-1",
                      "Egress": true,
                      "RuleAction": "deny"
                  },
                  {
                      "CidrBlock": "0.0.0.0/0",
                      "RuleNumber": 32767,
                      "Protocol": "-1",
                      "Egress": false,
                      "RuleAction": "deny"
                  }
              ],
              "IsDefault": false
          },
          {
              "Associations": [
                  {
                      "SubnetId": "subnet-6bea5f06",
                      "NetworkAclId": "acl-9aeb5ef7",
                      "NetworkAclAssociationId": "aclassoc-67ea5f0a"
                  },
                  {
                      "SubnetId": "subnet-65ea5f08",
                      "NetworkAclId": "acl-9aeb5ef7",
                      "NetworkAclAssociationId": "aclassoc-66ea5f0b"
                  }
              ],
              "NetworkAclId": "acl-9aeb5ef7",
              "VpcId": "vpc-98eb5ef5",
              "Tags": [],
              "Entries": [
                  {
                      "CidrBlock": "0.0.0.0/0",
                      "RuleNumber": 100,
                      "Protocol": "-1",
                      "Egress": true,
                      "RuleAction": "allow"
                  },
                  {
                      "CidrBlock": "0.0.0.0/0",
                      "RuleNumber": 32767,
                      "Protocol": "-1",
                      "Egress": true,
                      "RuleAction": "deny"
                  },
                  {
                      "CidrBlock": "0.0.0.0/0",
                      "RuleNumber": 100,
                      "Protocol": "-1",
                      "Egress": false,
                      "RuleAction": "allow"
                  },
                  {
                      "CidrBlock": "0.0.0.0/0",
                      "RuleNumber": 32767,
                      "Protocol": "-1",
                      "Egress": false,
                      "RuleAction": "deny"
                  }
              ],
              "IsDefault": true
          }          
      ]
  }
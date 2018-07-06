**To describe the longer ID settings for the root user and all IAM roles and IAM users that have explicitly specified a longer ID preference.**

This example describes ID format for the root user and all IAM roles and IAM users that have explicitly specified a longer ID preference. The output indicates that the following resource types can be enabled or disabled for longer IDs: bundle, conversion-task, customer-gateway, dhcp-options, elastic-ip-allocation, elastic-ip-association, export-task, flow-log, image, import-task, internet-gateway, network-acl, network-acl-association, network-interface, network-interface-attachment, prefix-list, route-table, route-table-association, security-group, subnet, subnet-cidr-block-association, vpc, vpc-cidr-block-association, vpc-endpoint, vpc-peering-connection, vpn-connection, and vpn-gateway. 

The ``Deadline`` value for the reservation, instance, volume, and snapshot resource types indicates that the deadline for those resources expired at 00:00 UTC on December 15, 2016. It also shows that the root account has enabled longer IDs for all supported resource types, while the ``user1`` IAM user has disabled longer IDs for image and bundle resource types, and the ``Admin`` IAM role has disable longer IDs for vpc and subnet resource types.

Command::

  aws ec2 describe-aggregate-id-format --region eu-west-1

Output::

  {
    "Statuses": [
        {
            "Resource": "reservation",
            "Deadline": "2016-12-15T12:00:00.000Z",
            "UseLongIds": true
        },
        {
            "Resource": "instance",
            "Deadline": "2016-12-15T12:00:00.000Z",
            "UseLongIds": true
        },
        {
            "Resource": "volume",
            "Deadline": "2016-12-15T12:00:00.000Z",
            "UseLongIds": true
        },
        {
            "Resource": "snapshot",
            "Deadline": "2016-12-15T12:00:00.000Z",
            "UseLongIds": true
        },
        {
            "UseLongIds": true,
            "Resource": "network-interface-attachment"
        },
        {
            "UseLongIds": true,
            "Resource": "network-interface"
        },
        {
            "UseLongIds": true,
            "Resource": "elastic-ip-allocation"
        },
        {
            "UseLongIds": true,
            "Resource": "elastic-ip-association"
        },
        {
            "UseLongIds": true,
            "Resource": "vpc"
        },
        {
            "UseLongIds": true,
            "Resource": "subnet"
        },
        {
            "UseLongIds": true,
            "Resource": "route-table"
        },
        {
            "UseLongIds": true,
            "Resource": "route-table-association"
        },
        {
            "UseLongIds": true,
            "Resource": "network-acl"
        },
        {
            "UseLongIds": true,
            "Resource": "network-acl-association"
        },
        {
            "UseLongIds": true,
            "Resource": "dhcp-options"
        },
        {
            "UseLongIds": true,
            "Resource": "internet-gateway"
        },
        {
            "UseLongIds": true,
            "Resource": "vpc-cidr-block-association"
        },
        {
            "UseLongIds": true,
            "Resource": "vpc-ipv6-cidr-block-association"
        },
        {
            "UseLongIds": true,
            "Resource": "subnet-ipv6-cidr-block-association"
        },
        {
            "UseLongIds": true,
            "Resource": "vpc-peering-connection"
        },
        {
            "UseLongIds": true,
            "Resource": "security-group"
        },
        {
            "UseLongIds": true,
            "Resource": "flow-log"
        },
        {
            "UseLongIds": true,
            "Resource": "conversion-task"
        },
        {
            "UseLongIds": true,
            "Resource": "export-task"
        },
        {
            "UseLongIds": true,
            "Resource": "import-task"
        },
        {
            "UseLongIds": true,
            "Resource": "image"
        },
        {
            "UseLongIds": true,
            "Resource": "bundle"
        },
        {
            "UseLongIds": true,
            "Resource": "vpc-endpoint"
        },
        {
            "UseLongIds": true,
            "Resource": "customer-gateway"
        },
        {
            "UseLongIds": true,
            "Resource": "vpn-connection"
        },
        {
            "UseLongIds": true,
            "Resource": "vpn-gateway"
        }
    ],
    "Arn": "arn:aws:iam::123456789098:root"
  },
  {
    "Statuses": [
        {
            "Resource": "reservation",
            "Deadline": "2016-12-15T12:00:00.000Z",
            "UseLongIds": true
        },
        {
            "Resource": "instance",
            "Deadline": "2016-12-15T12:00:00.000Z",
            "UseLongIds": true
        },
        {
            "Resource": "volume",
            "Deadline": "2016-12-15T12:00:00.000Z",
            "UseLongIds": true
        },
        {
            "Resource": "snapshot",
            "Deadline": "2016-12-15T12:00:00.000Z",
            "UseLongIds": true
        },
        {
            "UseLongIds": true,
            "Resource": "network-interface-attachment"
        },
        {
            "UseLongIds": true,
            "Resource": "network-interface"
        },
        {
            "UseLongIds": true,
            "Resource": "elastic-ip-allocation"
        },
        {
            "UseLongIds": true,
            "Resource": "elastic-ip-association"
        },
        {
            "UseLongIds": true,
            "Resource": "vpc"
        },
        {
            "UseLongIds": true,
            "Resource": "subnet"
        },
        {
            "UseLongIds": true,
            "Resource": "route-table"
        },
        {
            "UseLongIds": true,
            "Resource": "route-table-association"
        },
        {
            "UseLongIds": true,
            "Resource": "network-acl"
        },
        {
            "UseLongIds": true,
            "Resource": "network-acl-association"
        },
        {
            "UseLongIds": true,
            "Resource": "dhcp-options"
        },
        {
            "UseLongIds": true,
            "Resource": "internet-gateway"
        },
        {
            "UseLongIds": true,
            "Resource": "vpc-cidr-block-association"
        },
        {
            "UseLongIds": true,
            "Resource": "vpc-ipv6-cidr-block-association"
        },
        {
            "UseLongIds": true,
            "Resource": "subnet-ipv6-cidr-block-association"
        },
        {
            "UseLongIds": true,
            "Resource": "vpc-peering-connection"
        },
        {
            "UseLongIds": true,
            "Resource": "security-group"
        },
        {
            "UseLongIds": true,
            "Resource": "flow-log"
        },
        {
            "UseLongIds": true,
            "Resource": "conversion-task"
        },
        {
            "UseLongIds": true,
            "Resource": "export-task"
        },
        {
            "UseLongIds": true,
            "Resource": "import-task"
        },
        {
            "UseLongIds": false,
            "Resource": "image"
        },
        {
            "UseLongIds": false,
            "Resource": "bundle"
        },
        {
            "UseLongIds": true,
            "Resource": "vpc-endpoint"
        },
        {
            "UseLongIds": true,
            "Resource": "customer-gateway"
        },
        {
            "UseLongIds": true,
            "Resource": "vpn-connection"
        },
        {
            "UseLongIds": true,
            "Resource": "vpn-gateway"
        }
    ],
    "Arn": "arn:aws:iam::123456789098:user/user1"
  },
  {
    "Statuses": [
        {
            "Resource": "reservation",
            "Deadline": "2016-12-15T12:00:00.000Z",
            "UseLongIds": true
        },
        {
            "Resource": "instance",
            "Deadline": "2016-12-15T12:00:00.000Z",
            "UseLongIds": true
        },
        {
            "Resource": "volume",
            "Deadline": "2016-12-15T12:00:00.000Z",
            "UseLongIds": true
        },
        {
            "Resource": "snapshot",
            "Deadline": "2016-12-15T12:00:00.000Z",
            "UseLongIds": true
        },
        {
            "UseLongIds": true,
            "Resource": "network-interface-attachment"
        },
        {
            "UseLongIds": true,
            "Resource": "network-interface"
        },
        {
            "UseLongIds": true,
            "Resource": "elastic-ip-allocation"
        },
        {
            "UseLongIds": true,
            "Resource": "elastic-ip-association"
        },
        {
            "UseLongIds": false,
            "Resource": "vpc"
        },
        {
            "UseLongIds": false,
            "Resource": "subnet"
        },
        {
            "UseLongIds": true,
            "Resource": "route-table"
        },
        {
            "UseLongIds": true,
            "Resource": "route-table-association"
        },
        {
            "UseLongIds": true,
            "Resource": "network-acl"
        },
        {
            "UseLongIds": true,
            "Resource": "network-acl-association"
        },
        {
            "UseLongIds": true,
            "Resource": "dhcp-options"
        },
        {
            "UseLongIds": true,
            "Resource": "internet-gateway"
        },
        {
            "UseLongIds": true,
            "Resource": "vpc-cidr-block-association"
        },
        {
            "UseLongIds": true,
            "Resource": "vpc-ipv6-cidr-block-association"
        },
        {
            "UseLongIds": true,
            "Resource": "subnet-ipv6-cidr-block-association"
        },
        {
            "UseLongIds": true,
            "Resource": "vpc-peering-connection"
        },
        {
            "UseLongIds": true,
            "Resource": "security-group"
        },
        {
            "UseLongIds": true,
            "Resource": "flow-log"
        },
        {
            "UseLongIds": true,
            "Resource": "conversion-task"
        },
        {
            "UseLongIds": true,
            "Resource": "export-task"
        },
        {
            "UseLongIds": true,
            "Resource": "import-task"
        },
        {
            "UseLongIds": true,
            "Resource": "image"
        },
        {
            "UseLongIds": true,
            "Resource": "bundle"
        },
        {
            "UseLongIds": true,
            "Resource": "vpc-endpoint"
        },
        {
            "UseLongIds": true,
            "Resource": "customer-gateway"
        },
        {
            "UseLongIds": true,
            "Resource": "vpn-connection"
        },
        {
            "UseLongIds": true,
            "Resource": "vpn-gateway"
        }
    ]
    "Arn": "arn:aws:iam::123456789098:role/Admin"
  }

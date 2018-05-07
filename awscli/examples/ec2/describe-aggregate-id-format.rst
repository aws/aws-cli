**To describe the longer ID format settings for all resource types in a specific region**

This example describes the overall longer ID format settings for the eu-west-1 Region. The output indicates that the following resource types can be enabled or disabled for longer IDs: bundle, conversion-task, customer-gateway, dhcp-options, elastic-ip-allocation, elastic-ip-association, export-task, flow-log, image, import-task, internet-gateway, network-acl, network-acl-association, network-interface, network-interface-attachment, prefix-list, route-table, route-table-association, security-group, subnet, subnet-cidr-block-association, vpc, vpc-cidr-block-association, vpc-endpoint, vpc-peering-connection, vpn-connection, and vpn-gateway. 

The ``Deadline`` value for the reservation, instance, volume, and snapshot resource types indicates that the deadline for those resources expired at 00:00 UTC on December 15, 2016. It also shows that all IAM users and IAM roles are configured to use longer IDs for all resource types, except vpc and subnet. One or more IAM users or IAM roles are not configured to use longer IDs for vpc and subnet resource types. ``UseLongIdsAggregated`` is ``false`` because not all IAM users and IAM roles are configured to use longer IDs for all resource types in the Region.

Command::

  aws ec2 describe-aggregate-id-format --region eu-west-1

Output::

  {
    "UseLongIdsAggregated": false,
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
    {
  }

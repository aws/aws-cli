**To list the resource record sets in a hosted zone**

The following ``list-resource-record-sets`` example lists summary information about the first 100 resource record sets in a specified hosted zone. ::

    aws route53 list-resource-record-sets \
        --hosted-zone-id Z2LD58HEXAMPLE

Output::

    {
        "ResourceRecordSets": [
            {
                "Name": "example.domain.",
                "Type": "NS",
                "TTL": 172800,
                "ResourceRecords": [
                    {
                        "Value": "ns-2048.awsdns-64.com."
                    },
                    {
                        "Value": "ns-2049.awsdns-65.net."
                    },
                    {
                        "Value": "ns-2050.awsdns-66.org."
                    },
                    {
                        "Value": "ns-2051.awsdns-67.co.uk."
                    }
                ]
            },
            {
                "Name": "example.domain.",
                "Type": "SOA",
                "TTL": 900,
                "ResourceRecords": [
                    {
                        "Value": "ns-2048.awsdns-64.com. awsdns-hostmaster.amazon.com. 1 7200 900 1209600 86400"
                    }
                ]
            }
        ]
    }

If the hosted zone contains more than 100 resource record sets, or if you want to list them in groups smaller than 100, include the ``--maxitems`` parameter. For example, to list resource record sets one at a time, use the following command. ::

    aws route53 list-resource-record-sets \
        --hosted-zone-id Z2LD58HEXAMPLE \
        --max-items 1

To view information about the next resource record set in the hosted zone, take the value of ``NextToken`` from the response to the previous command, and include it in the ``--starting-token`` parameter, as shown in the following example. ::

    aws route53 list-resource-record-sets \
        --hosted-zone-id Z2LD58HEXAMPLE \
        --max-items 1 \
        --starting-token Z3M3LMPEXAMPLE

To view all the resource record sets of a particular name, use the ``--query`` parameter to filter them out, as shown in the following example. ::

    aws route53 list-resource-record-sets \
        --hosted-zone-id Z2LD58HEXAMPLE \
        --query "ResourceRecordSets[?Name == 'example.domain.']"

For more information, see `Listing records <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resource-record-sets-listing.html>`__ in the *Amazon Route 53 Developer Guide*.

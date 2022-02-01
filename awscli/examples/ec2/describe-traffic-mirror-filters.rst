**To view your traffic mirror filters**

The following ``describe-traffic-mirror-filters`` example displays details for all of your traffic mirror filters. ::

    aws ec2 describe-traffic-mirror-filters

Output::

    {
        "TrafficMirrorFilters": [
            {
                "TrafficMirrorFilterId": "tmf-0293f26e86EXAMPLE",
                "IngressFilterRules": [
                    {
                        "TrafficMirrorFilterRuleId": "tmfr-0ca76e0e08EXAMPLE",
                        "TrafficMirrorFilterId": "tmf-0293f26e86EXAMPLE",
                        "TrafficDirection": "ingress",
                        "RuleNumber": 100,
                        "RuleAction": "accept",
                        "Protocol": 6,
                        "DestinationCidrBlock": "10.0.0.0/24",
                        "SourceCidrBlock": "10.0.0.0/24",
                        "Description": "TCP Rule"
                    }
                ],
                "EgressFilterRules": [],
                "NetworkServices": [],
                "Description": "Exanple Filter",
                "Tags": []
            }
        ]
    }

For more information, see `View Your Traffic Mirror Filters <https://docs.aws.amazon.com/vpc/latest/mirroring/traffic-mirroring-filter.html#view-traffic-mirroring-filter>`__ in the *AWS Traffic Mirroring Guide*.

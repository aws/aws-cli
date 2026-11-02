**To create a traffic mirror filter**

The following ``create-traffic-mirror-filter`` example creates a traffic mirror filter. After you create the filter, use ``create-traffic-mirror-filter-rule`` to add rules. ::

    aws ec2 create-traffic-mirror-filter \
        --description 'TCP Filter'

Output::

    {
        "ClientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "TrafficMirrorFilter": {
            "TrafficMirrorFilterId": "tmf-04812ff784EXAMPLE",
            "Description": "TCP Filter",
            "EgressFilterRules": [],
            "IngressFilterRules": [],
            "Tags": [],
            "NetworkServices": []
        }
    }

For more information, see `Create a traffic mirror filter <https://docs.aws.amazon.com/vpc/latest/mirroring/create-traffic-mirroring-filter.html>`__ in the *Traffic Mirroring Guide*.
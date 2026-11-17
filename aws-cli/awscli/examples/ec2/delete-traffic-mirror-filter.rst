**To delete a traffic mirror filter**

The following ``delete-traffic-mirror-filter`` example deletes the specified traffic mirror filter. ::

    aws ec2 delete-traffic-mirror-filter \
        --traffic-mirror-filter-id tmf-0be0b25fcdEXAMPLE

Output::

    {
        "TrafficMirrorFilterId": "tmf-0be0b25fcdEXAMPLE"
    }

For more information, see `Create, modify, or delete a traffic mirror filter <https://docs.aws.amazon.com/vpc/latest/mirroring/create-traffic-mirroring-filter.html>`__ in the *AWS Traffic Mirroring Guide*.

**To get firewall information for an instance**

The following ``get-instance-port-states`` example returns the firewall ports configured for instance ``MEAN-1``. ::

    aws lightsail get-instance-port-states \
        --instance-name MEAN-1

Output::

    {
        "portStates": [
            {
                "fromPort": 80,
                "toPort": 80,
                "protocol": "tcp",
                "state": "open"
            },
            {
                "fromPort": 22,
                "toPort": 22,
                "protocol": "tcp",
                "state": "open"
            },
            {
                "fromPort": 443,
                "toPort": 443,
                "protocol": "tcp",
                "state": "open"
            }
        ]
    }

For more information, see `Control instance traffic with firewalls in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-firewall-and-port-mappings-in-amazon-lightsail.html>`__ in the *Amazon Lightsail User Guide*.

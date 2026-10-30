**To get information about the state of an instance**

The following ``get-instance-state`` example returns the state of the specified instance. ::

    aws lightsail get-instance-state \
        --instance-name MEAN-1

Output::

    {
        "state": {
            "code": 16,
            "name": "running"
        }
    }

For more information, see `Virtual private server instances in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-instances-virtual-private-servers-in-amazon-lightsail.html>`__ in the *Amazon Lightsail User Guide*.

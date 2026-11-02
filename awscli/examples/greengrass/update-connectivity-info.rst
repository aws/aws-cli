**To update the connectivity information for a Greengrass core**

The following ``update-connectivity-info`` example changes the endpoints that devices can use to connect to the specified Greengrass core. Connectivity information is a list of IP addresses or domain names, with corresponding port numbers and optional customer-defined metadata. You might need to update connectivity information when the local network changes. ::

    aws greengrass update-connectivity-info \
        --thing-name "MyGroup_Core" \
        --connectivity-info "[{\"Metadata\":\"\",\"PortNumber\":8883,\"HostAddress\":\"127.0.0.1\",\"Id\":\"localhost_127.0.0.1_0\"},{\"Metadata\":\"\",\"PortNumber\":8883,\"HostAddress\":\"192.168.1.3\",\"Id\":\"localIP_192.168.1.3\"}]"

Output::

    {
        "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Configure the MQTT port for local messaging <https://docs.aws.amazon.com/greengrass/v1/developerguide/gg-core.html#config-local-mqtt-port>`__ in the *AWS IoT Greengrass Version 1 Developer Guide*.

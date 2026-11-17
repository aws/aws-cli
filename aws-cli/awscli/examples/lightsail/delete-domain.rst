**To delete a domain (DNS zone)**

The following ``delete-domain`` example deletes the specified domain and all of the entries in the domain (DNS records). 

**Note:** Lightsail's domain-related API operations are available in only the ``us-east-1`` Region. If your CLI profile is configured to use a different Region, you must include the ``--region us-east-1`` parameter or the command fails. ::

    aws lightsail delete-domain \
        --region us-east-1 \
        --domain-name example.com

Output::

    {
        "operation": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "resourceName": "example.com",
            "resourceType": "Domain",
            "createdAt": 1569873788.13,
            "location": {
                "availabilityZone": "all",
                "regionName": "global"
            },
            "isTerminal": true,
            "operationType": "DeleteDomain",
            "status": "Succeeded",
            "statusChangedAt": 1569873788.13
        }
    }

For more information, see `Delete a DNS zone in Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-delete-dns-zone.html>`__ in the *Amazon Lightsail User Guide*.

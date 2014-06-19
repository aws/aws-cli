**1. To add tags to a cluster**

- Command::

    aws emr add-tags --resource-id j-XXXXXXYY --tags name="John Doe" age=29
    male address="123 East NW Seattle"

- Output::

    None

**2. To list tags of a cluster**

--Command::

  aws emr describe-cluster --cluster-id j-XXXXXXYY --query Cluster.Tags

- Output::

    [
        {
            "Value": "John Doe",
            "Key": "Name"
        },
        {
            "Value": "29",
            "Key": "age"
        },
        {
            "Value": "",
            "Key": "male"
        },
        {
            "Value": "",
            "Key": "male"
        },
        {
            "Value": "123 East NW Seattle",
            "Key": "address"
        }
    ]

### To list all iOS private devices and their UDID value

```bash
aws devicefarm list-devices --region us-west-2 --query 'devices[?platform==`IOS` && fleetType==`PRIVATE`].[name, os, instances[].udid]'
```

**Example output**

```
[
    [
        "Apple iPad Mini 4",
        "9.3.1",
        [
            "THE_UDID_VALUE_HERE"
        ]
    ],
    ...
    [
        "Apple iPhone SE",
        "10.3.2",
        [
            "THE_UDID_VALUE_HERE"
        ]
    ]
]
```

**To list trusted IP sets in the current region**

The following ``list-ip-sets`` example lists the trusted IP sets in your current AWS region. ::

    aws guardduty list-ip-sets \
        --detector-id 12abc34d567e8fa901bc2d34eexample 

Output::

    {
        "IpSetIds": [
            "d4b94fc952d6912b8f3060768example"
        ]
    }

For more information, see `Customizing threat detection with entity lists and IP address lists <https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_upload-lists.html>`__ in the *Amazon GuardDuty User Guide*.
    
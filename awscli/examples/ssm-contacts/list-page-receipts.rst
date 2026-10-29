**To list page receipts**

The following ``list-page-receipts`` example lists whether a page was received or not by a contact. ::

    aws ssm-contacts list-page-receipts \
        --page-id "arn:aws:ssm-contacts:us-west-2:123456789012:page/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "Receipts": [
            {
                "ContactChannelArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact-channel/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "ReceiptType": "DELIVERED",
                "ReceiptInfo": "425440",
                "ReceiptTime": "2021-05-18T20:42:57.485000+00:00"
            },
            {
                "ContactChannelArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact-channel/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "ReceiptType": "READ",
                "ReceiptInfo": "425440",
                "ReceiptTime": "2021-05-18T20:42:57.907000+00:00"
            },
            {
                "ContactChannelArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact-channel/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "ReceiptType": "SENT",
                "ReceiptInfo": "SM6656c19132f1465f9c9c1123a5dde7c9",
                "ReceiptTime": "2021-05-18T20:40:52.962000+00:00"
            }
        ]
    }

For more information, see `Contacts <https://docs.aws.amazon.com/incident-manager/latest/userguide/contacts.html>`__ in the *Incident Manager User Guide*.
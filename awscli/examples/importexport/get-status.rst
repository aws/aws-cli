**To get the status of a job**

The following ``get-status`` example returns the status of the specified job. ::

    aws importexport get-status \
        --job-id EX1ID

Output::

    {
        "JobId": "EX1ID",
        "JobType": "Import",
        "LocationCode": "NotReceived",
        "LocationMessage": "AWS has not received your device.",
        "ProgressCode": "Pending",
        "ProgressMessage": "The specified job has not started.",
        "ErrorCount": 0,
        "Signature": "ktKDXpdbEXAMPLEyGFJmQO744UHw=",
        "SignatureFileContents": "version:2.0\nsigningMethod:HmacSHA1\njobId:EX1ID\nsignature:ktKDXpdbEXAMPLEyGFJmQO744UHw=",
        "CurrentManifest": "manifestVersion:2.0\ngenerator:Text editor\nbucket:amzn-s3-demo-bucket\ndeviceId:49382\neraseDevice:yes\nnotificationEmail:john.doe@example.com;jane.roe@example.com\ntrueCryptPassword:password123\nacl:private\nserviceLevel:standard\nreturnAddress:\n    name: Jane Roe\n    company: Example Corp.\n    street1: 123 Any Street\n    street2:\n    street3:\n    city: Anytown\n    stateOrProvince: WA\n    postalCode: 91011-1111\n    country:USA\n    phoneNumber:206-555-1111",
        "CreationDate": "2015-05-27T18:58:21Z"
    }

When you ship your device, it will be delivered to a sorting facility, and then forwarded on to an AWS data center. Note that when you send a get-status command, the status of your job will not show as ``At AWS`` until the shipment has been received at the AWS data center.

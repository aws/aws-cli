**To update a job**

The following ``update-job`` example updates the specified job. ::

    aws importexport update-job \
        --job-id EX1ID \
        --job-type import \
        --manifest file://manifest.txt \
        --no-validate-only

Contents of ``manifest.txt``::

    manifestVersion: 2.0;
    returnAddress:
        name: Jane Roe
        company: Example Corp.
        street1: 123 Any Street
        city: Anytown
        stateOrProvince: WA
        postalCode: 91011-1111
        phoneNumber: 206-555-1111
        country: USA
    deviceId: 49382
    eraseDevice: yes
    notificationEmail: john.doe@example.com;jane.roe@example.com
    bucket: amzn-s3-demo-bucket

Output::

    {
        "Success": true,
        "WarningMessage": "**** Device will be erased before being returned. ****"
    }

With this command, you can either modify the original manifest you submitted, or you can start over and create a new manifest file. In either case, the original manifest is discarded.

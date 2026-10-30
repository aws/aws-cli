**To create an import job**

The following ``create-job`` example creates an import job from a manifest file. ::

    aws importexport create-job \
        --job-type import \
        --manifest file://manifest \
        --no-validate-only

The file ``manifest`` is a YAML formatted text file in the current directory.

Contents of ``manifest``::

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
        "JobId": "EX1ID",
        "JobType": "Import",
        "Signature": "ktKDXpdbEXAMPLEyGFJmQO744UHw=",
        "SignatureFileContents": "version:2.0\nsigningMethod:HmacSHA1\njobId:EX1ID\nsignature:ktKDXpdbEXAMPLEyGFJmQO744UHw=",
        "WarningMessage": "**** Device will be erased before being returned. ****"
    }

You can also pass the manifest as a string in quotes. ::

    aws importexport create-job \
        --job-type import \
        --manifest 'manifestVersion: 2.0;
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
        bucket: amzn-s3-demo-bucket'

For information on quoting string arguments and using files, see `Specifying parameter values in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-parameters.html>`__ in the *AWS CLI User Guide*.

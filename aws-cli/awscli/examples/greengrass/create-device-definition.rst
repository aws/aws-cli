**To create a device definition**

The following ``create-device-definition`` example creates a device definition that contains an initial device definition version. The initial version defines two devices.
Before you can create a Greengrass device, you must first create and provision the corresponding AWS IoT thing. This process includes the following ``iot`` commands that you must run to get the required information for the Greengrass command:

* Create the AWS IoT thing that corresponds to the device. ::

    aws iot create-thing \
        --thing-name "InteriorTherm"

Output::

    {
        "thingArn": "arn:aws:iot:us-west-2:123456789012:thing/InteriorTherm",
        "thingName": "InteriorTherm",
        "thingId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

* Create public and private keys and the device certificate for the thing. This example uses the ``create-keys-and-certificate`` command and requires write permissions to the current directory. Alternatively, you can use the ``create-certificate-from-csr`` command. ::

    aws iot create-keys-and-certificate \
        --set-as-active \
        --certificate-pem-outfile "myDevice.cert.pem" \
        --public-key-outfile "myDevice.public.key" \
        --private-key-outfile "myDevice.private.key"

Output::

    {
        "certificateArn": "arn:aws:iot:us-west-2:123456789012:cert/66a415ec415668c2349a76170b64ac0878231c1e21ec83c10e92a18bd568eb92",
        "certificatePem": "-----BEGIN CERTIFICATE-----\nMIIDWTCAkGgAwIBATgIUCgq6EGqou6zFqWgIZRndgQEFW+gwDQYJKoZIhvc...KdGewQS\n-----END CERTIFICATE-----\n",
        "keyPair": {
            "PublicKey": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBzrqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAqKpRgnn6yq26U3y...wIDAQAB\n-----END PUBLIC KEY-----\n",
            "PrivateKey": "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIABAKCAQEAqKpRgnn6yq26U3yt5YFZquyukfRjbMXDcNOK4rMCxDR...fvY4+te\n-----END RSA PRIVATE KEY-----\n"
        },
        "certificateId": "66a415ec415668c2349a76170b64ac0878231c1e21ec83c10e92a18bd568eb92"
    }

* Create an AWS IoT policy that allows ``iot`` and ``greengrass`` actions. For simplicity, the following policy allows actions on all resources, but your policy can be more restrictive. ::

    aws iot create-policy \
        --policy-name "GG_Devices" \
        --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"iot:Publish\",\"iot:Subscribe\",\"iot:Connect\",\"iot:Receive\"],\"Resource\":[\"*\"]},{\"Effect\":\"Allow\",\"Action\":[\"iot:GetThingShadow\",\"iot:UpdateThingShadow\",\"iot:DeleteThingShadow\"],\"Resource\":[\"*\"]},{\"Effect\":\"Allow\",\"Action\":[\"greengrass:*\"],\"Resource\":[\"*\"]}]}"

Output::

    {
        "policyName": "GG_Devices",
        "policyArn": "arn:aws:iot:us-west-2:123456789012:policy/GG_Devices",
        "policyDocument": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"iot:Publish\",\"iot:Subscribe\",\"iot:Connect\",\"iot:Receive\"],\"Resource\":[\"*\"]},{\"Effect\":\"Allow\",\"Action\":[\"iot:GetThingShadow\",\"iot:UpdateThingShadow\",\"iot:DeleteThingShadow\"],\"Resource\":[\"*\"]},{\"Effect\":\"Allow\",\"Action\":[\"greengrass:*\"],\"Resource\":[\"*\"]}]}",
        "policyVersionId": "1"
    }

* Attach the policy to the certificate. ::

    aws iot attach-policy \
        --policy-name "GG_Devices" \
        --target "arn:aws:iot:us-west-2:123456789012:cert/66a415ec415668c2349a76170b64ac0878231c1e21ec83c10e92a18bd568eb92"

* Attach the thing to the certificate. ::

    aws iot attach-thing-principal \
        --thing-name "InteriorTherm" \
        --principal "arn:aws:iot:us-west-2:123456789012:cert/66a415ec415668c2349a76170b64ac0878231c1e21ec83c10e92a18bd568eb92"

After you create and configure the IoT thing as shown above, use the ``ThingArn`` and ``CertificateArn`` from the first two commands in the following example. ::

    aws greengrass create-device-definition \
        --name "Sensors" \
        --initial-version "{\"Devices\":[{\"Id\":\"InteriorTherm\",\"ThingArn\":\"arn:aws:iot:us-west-2:123456789012:thing/InteriorTherm\",\"CertificateArn\":\"arn:aws:iot:us-west-2:123456789012:cert/66a415ec415668c2349a76170b64ac0878231c1e21ec83c10e92a18bd568eb92\",\"SyncShadow\":true},{\"Id\":\"ExteriorTherm\",\"ThingArn\":\"arn:aws:iot:us-west-2:123456789012:thing/ExteriorTherm\",\"CertificateArn\":\"arn:aws:iot:us-west-2:123456789012:cert/6c52ce1b47bde88a637e9ccdd45fe4e4c2c0a75a6866f8f63d980ee22fa51e02\",\"SyncShadow\":true}]}"

Output::

    {
        "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/devices/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
        "Name": "Sensors",
        "LastUpdatedTimestamp": "2019-09-11T00:11:06.197Z",
        "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
        "CreationTimestamp": "2019-09-11T00:11:06.197Z",
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/devices/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Overview of the AWS IoT Greengrass group object model <https://docs.aws.amazon.com/greengrass/v1/developerguide/deployments.html#api-overview>`__ in the *AWS IoT Greengrass Developer Guide*.

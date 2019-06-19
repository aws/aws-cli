**To create a policy**

The following ``create-policy`` example creates a policy that allows updates to all AWS IoT device certificates. ::

    aws iot create-policy \
        --policy-name "UpdateDeviceCertPolicy" \
        --policy-document "{ \"Version\": \"2012-10-17\", \"Statement\": [ { \"Effect\": \"Allow\", \"Action\":  \"iot:UpdateCertificate\", \"Resource\": \"*\" } ] }"

Output::

    {
        "policyName": "UpdateDeviceCertPolicy",
        "policyArn": "arn:aws:iot:us-west-2:123456789012:policy/UpdateDeviceCertPolicy",
        "policyDocument": "{ \"Version\": \"2012-10-17\", \"Statement\": [ { \"Effect\": \"Allow\", \"Action\":  \"iot:UpdateCertificate\", \"Resource\": \"*\" } ] }",
        "policyVersionId": "1"
    }

For more information, see `AWS IoT Policies <https://docs.aws.amazon.com/iot/latest/developerguide/iot-policies.html>`__ in the *AWS IoT Developers Guide*.


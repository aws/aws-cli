**To list the tags attached to an IoT Device Advisor resource**

The following ``list-tags-for-resource`` example lists the tags attached to a device advisor resource. The device advisor resource can be a Suitedefinition-Arn or a Suiterun-Arn. ::

    aws iotdeviceadvisor list-tags-for-resource \
        --resource-arn arn:aws:iotdeviceadvisor:us-west-2:123456789012:suitedefinition/ba0uyjpg38ny

Output::

    {
        "tags": {
            "TestTagKey": "TestTagValue"
        }
    }

For more information, see `Resource types defined by AWS IoT Core Device Advisor <https://docs.aws.amazon.com/service-authorization/latest/reference/list_iotdeviceadvisor.html#list_iotdeviceadvisor-resources-for-iam-policies>`__ in the *Service Authorization Reference* and `Tagging your AWS IoT resources <https://docs.aws.amazon.com/iot/latest/developerguide/tagging-iot.html>`__ in the *AWS IoT Core Developer Guide*.

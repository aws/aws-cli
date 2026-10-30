**To remove the existing tags from an IoT Device Advisor resource**

The following ``untag-resource`` example removes the existing tags from a device advisor resource with the specified resource arn and tag key. The device advisor resource can be a Suitedefinition-Arn or a Suiterun-Arn. ::

    aws iotdeviceadvisor untag-resource \
        --resource-arn arn:aws:iotdeviceadvisor:us-west-2:123456789012:suitedefinition/ba0uyjpg38ny \
        --tag-keys "TagKey"

This command produces no output.

For more information, see `Resource types defined by AWS IoT Core Device Advisor <https://docs.aws.amazon.com/service-authorization/latest/reference/list_iotdeviceadvisor.html#list_iotdeviceadvisor-resources-for-iam-policies>`__ in the *Service Authorization Reference* and `Tagging your AWS IoT resources <https://docs.aws.amazon.com/iot/latest/developerguide/tagging-iot.html>`__ in the *AWS IoT Core Developer Guide*.

**To describe a domain configuration**

The following ``describe-domain-configuration`` example displays details about the specified domain configuration. ::

    aws iot describe-domain-configuration \
        --domain-configuration-name "additionalDataDomain"

Output::

    {    
        "domainConfigurationName": "additionalDataDomain",   
        "domainConfigurationArn": "arn:aws:iot:us-west-2:123456789012:domainconfiguration/additionalDataDomain/dikMh",   
        "domainName": "d01645582h24k4we2vblw-ats.iot.us-west-2.amazonaws.com",   
        "serverCertificates": [],   
        "domainConfigurationStatus": "ENABLED",  
        "serviceType": "DATA",  
        "domainType": "AWS_MANAGED"
    }

For more information, see `Configurable Endpoints <https://docs.aws.amazon.com/iot/latest/developerguide/iot-custom-endpoints-configurable-aws.html>`__ in the *AWS IoT Developer Guide*.

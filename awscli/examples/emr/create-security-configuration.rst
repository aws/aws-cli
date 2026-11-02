**Example 1: To create a security configuration with in-transit encryption enabled with PEM for certificate provider, and at-rest encryption enabled with SSE-S3 for S3 encryption and AWS-KMS for local disk key provider**

The following ``create-security-configuration`` example creates a security configuration named ``MySecurityConfig`` with in-transit encryption enabled with PEM for certificate provider, and at-rest encryption enabled with SSE-S3 for S3 encryption and AWS-KMS for local disk key provider. ::

    aws emr create-security-configuration \
        --name MySecurityConfig \
        --security-configuration '{
            "EncryptionConfiguration": {
                "EnableInTransitEncryption" : true,
                "EnableAtRestEncryption" : true,
                "InTransitEncryptionConfiguration" : {
                    "TLSCertificateConfiguration" : {
                        "CertificateProviderType" : "PEM",
                        "S3Object" : "s3://amzn-s3-demo-bucket/artifacts/MyCerts.zip"
                    }
                },
                "AtRestEncryptionConfiguration" : {
                    "S3EncryptionConfiguration" : {
                        "EncryptionMode" : "SSE-S3"
                    },
                    "LocalDiskEncryptionConfiguration" : {
                        "EncryptionKeyProviderType" : "AwsKms",
                        "AwsKmsKey" : "arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
                    }
                }
            }
        }'

Output::

    {
        "CreationDateTime": "2016-09-16T20:08:09.129000-0400",
        "Name": "MySecurityConfig"
    }

The following ``create-security-configuration`` example creates the same security configuration by using the ``security_configuration.json`` file. ::

    aws emr create-security-configuration \
        --name "MySecurityConfig" \
        --security-configuration file://./security_configuration.json

Contents of ``security_configuration.json``::

    {
        "EncryptionConfiguration": {
            "EnableInTransitEncryption": true,
            "EnableAtRestEncryption": true,
            "InTransitEncryptionConfiguration": {
                "TLSCertificateConfiguration": {
                    "CertificateProviderType": "PEM",
                    "S3Object": "s3://amzn-s3-demo-bucket/artifacts/MyCerts.zip"
                }
            },
            "AtRestEncryptionConfiguration": {
                "S3EncryptionConfiguration": {
                    "EncryptionMode": "SSE-S3"
                },
                "LocalDiskEncryptionConfiguration": {
                    "EncryptionKeyProviderType": "AwsKms",
                    "AwsKmsKey": "arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
                }
            }
        }
    }

Output::

    {
        "CreationDateTime": "2016-09-16T20:08:09.129000-0400",
        "Name": "MySecurityConfig"
    }

**Example 2: To create a security configuration with Kerberos enabled using cluster-dedicated KDC and cross-realm trust**

The following ``create-security-configuration`` example creates a security configuration named ``MySecurityConfig`` with Kerberos enabled using cluster-dedicated KDC and cross-realm trust. ::

    aws emr create-security-configuration \
        --name MySecurityConfig \
        --security-configuration '{
            "AuthenticationConfiguration": {
                "KerberosConfiguration": {
                    "Provider": "ClusterDedicatedKdc",
                    "ClusterDedicatedKdcConfiguration": {
                        "TicketLifetimeInHours": 24,
                        "CrossRealmTrustConfiguration": {
                            "Realm": "AD.DOMAIN.COM",
                            "Domain": "ad.domain.com",
                            "AdminServer": "ad.domain.com",
                            "KdcServer": "ad.domain.com"
                        }
                    }
                }
            }
        }'

Output::

    {
        "CreationDateTime": "2017-03-22T19:32:38.982000-0400",
        "Name": "MySecurityConfig"
    }

The following ``create-security-configuration`` example creates the same security configuration by using the ``security_configuration.json`` file. ::

    aws emr create-security-configuration \
        --name "MySecurityConfig" \
        --security-configuration file://./security_configuration.json

Contents of ``security_configuration.json``::

    {
        "AuthenticationConfiguration": {
            "KerberosConfiguration": {
                "Provider": "ClusterDedicatedKdc",
                "ClusterDedicatedKdcConfiguration": {
                    "TicketLifetimeInHours": 24,
                    "CrossRealmTrustConfiguration": {
                        "Realm": "AD.DOMAIN.COM",
                        "Domain": "ad.domain.com",
                        "AdminServer": "ad.domain.com",
                        "KdcServer": "ad.domain.com"
                    }
                }
            }
        }
    }

Output::

    {
        "CreationDateTime": "2017-03-22T19:32:38.982000-0400",
        "Name": "MySecurityConfig"
    }

For more information, see `Create a security configuration with the Amazon EMR console or with the AWS CLI <https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-create-security-configuration.html>`__ in the *Amazon EMR Management Guide*.

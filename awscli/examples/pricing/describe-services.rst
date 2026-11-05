**To retrieve service metadata**

The following ``describe-services`` example retrieves the metadata for the Amazon EC2 service code. ::

    aws pricing describe-services \
        --service-code AmazonEC2 \
        --format-version aws_v1 \
        --max-items 1

Output::

    {
        "Services": [
            {
                "ServiceCode": "AmazonEC2",
                "AttributeNames": [
                    "volumeType",
                    "maxIopsvolume",
                    "instance",
                    "instanceCapacity10xlarge",
                    "locationType",
                    "instanceFamily",
                    "operatingSystem",
                    "clockSpeed",
                    "LeaseContractLength",
                    "ecu",
                    "networkPerformance",
                    "instanceCapacity8xlarge",
                    "group",
                    "maxThroughputvolume",
                    "gpuMemory",
                    "ebsOptimized",
                    "elasticGpuType",
                    "maxVolumeSize",
                    "gpu",
                    "processorFeatures",
                    "intelAvxAvailable",
                    "instanceCapacity4xlarge",
                    "servicecode",
                    "groupDescription",
                    "processorArchitecture",
                    "physicalCores",
                    "productFamily",
                    "enhancedNetworkingSupported",
                    "intelTurboAvailable",
                    "memory",
                    "dedicatedEbsThroughput",
                    "vcpu",
                    "OfferingClass",
                    "instanceCapacityLarge",
                    "capacitystatus",
                    "termType",
                    "storage",
                    "intelAvx2Available",
                    "storageMedia",
                    "physicalProcessor",
                    "provisioned",
                    "servicename",
                    "PurchaseOption",
                    "instanceCapacity18xlarge",
                    "instanceType",
                    "tenancy",
                    "usagetype",
                    "normalizationSizeFactor",
                    "instanceCapacity2xlarge",
                    "instanceCapacity16xlarge",
                    "maxIopsBurstPerformance",
                    "instanceCapacity12xlarge",
                    "instanceCapacity32xlarge",
                    "instanceCapacityXlarge",
                    "licenseModel",
                    "currentGeneration",
                    "preInstalledSw",
                    "location",
                    "instanceCapacity24xlarge",
                    "instanceCapacity9xlarge",
                    "instanceCapacityMedium",
                    "operation"
                ]
            }
        ],
        "FormatVersion": "aws_v1"
    }

For more information, see `Finding services and products using AWS Price List Query API <https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/using-price-list-query-api.html>`__ in the *AWS Billing User Guide*.

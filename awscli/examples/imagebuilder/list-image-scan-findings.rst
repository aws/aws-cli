**To list vulnerability findings for an image build**

The following ``list-image-scan-findings`` example lists the vulnerability findings that Amazon Inspector detected for the specified image build version. ::

    aws imagebuilder list-image-scan-findings \
        --filters name=imageBuildVersionArn,values=arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "findings": [
            {
                "awsAccountId": "123456789012",
                "imageBuildVersionArn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1",
                "imagePipelineArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-pipeline/my-example-pipeline",
                "type": "PACKAGE_VULNERABILITY",
                "description": "In the Linux kernel, the following vulnerability has been resolved:\n\nvirtio: break and reset virtio devices on device_shutdown()",
                "title": "CVE-2025-38064 - kernel",
                "remediation": {
                    "recommendation": {
                        "text": "None Provided"
                    }
                },
                "severity": "HIGH",
                "firstObservedAt": "2026-01-06T20:12:57+00:00",
                "updatedAt": "2026-01-06T20:12:57+00:00",
                "inspectorScore": 7.0,
                "inspectorScoreDetails": {
                    "adjustedCvss": {
                        "scoreSource": "AMAZON_CVE",
                        "cvssSource": "AMAZON_CVE",
                        "version": "3.1",
                        "score": 7.0,
                        "scoringVector": "CVSS:3.1/AV:L/AC:H/PR:L/UI:N/S:U/C:H/I:H/A:H",
                        "adjustments": []
                    }
                },
                "packageVulnerabilityDetails": {
                    "vulnerabilityId": "CVE-2025-38064",
                    "vulnerablePackages": [
                        {
                            "name": "kernel",
                            "version": "4.14.355",
                            "epoch": 0,
                            "release": "280.652.amzn2",
                            "arch": "X86_64",
                            "packageManager": "OS",
                            "fixedInVersion": "0:5.15.189-131.202.amzn2",
                            "remediation": "yum update kernel"
                        }
                    ],
                    "source": "AMAZON_CVE",
                    "cvss": [
                        {
                            "baseScore": 7.0,
                            "scoringVector": "CVSS:3.1/AV:L/AC:H/PR:L/UI:N/S:U/C:H/I:H/A:H",
                            "version": "3.1",
                            "source": "AMAZON_CVE"
                        }
                    ],
                    "relatedVulnerabilities": [
                        "ALAS2-2025-2955",
                        "ALAS2023-2025-1130"
                    ],
                    "sourceUrl": "https://alas.aws.amazon.com/cve/json/v1/CVE-2025-38064.json",
                    "vendorSeverity": "Important",
                    "vendorCreatedAt": "2025-06-18T00:00:00+00:00",
                    "vendorUpdatedAt": "2025-06-25T00:00:00+00:00",
                    "referenceUrls": [
                        "https://alas.aws.amazon.com/AL2/ALAS2-2025-2955.html",
                        "https://alas.aws.amazon.com/AL2023/ALAS2023-2025-1130.html"
                    ]
                },
                "fixAvailable": "YES"
            }
        ]
    }

For more information, see `Manage security findings for Image Builder images <https://docs.aws.amazon.com/imagebuilder/latest/userguide/image-security-findings.html>`__ in the *EC2 Image Builder User Guide*.

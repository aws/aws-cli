**To export a VM from an AMI**

The following ``export-image`` example exports the specified AMI to the specified bucket in the specified format. ::

    aws ec2 export-image \
        --image-id ami-1234567890abcdef0 \
        --disk-image-format VMDK \
        --s3-export-location S3Bucket=my-export-bucket,S3Prefix=exports/

Output::

    {
        "DiskImageFormat": "vmdk",
        "ExportImageTaskId": "export-ami-1234567890abcdef0",
        "ImageId": "ami-1234567890abcdef0",
        "RoleName": "vmimport",
        "Progress": "0",
        "S3ExportLocation": {
            "S3Bucket": "my-export-bucket",
            "S3Prefix": "exports/"
        },
        "Status": "active",
        "StatusMessage": "validating"
    }

For more information, see `Export a VM from an Amazon Machine Image (AMI) using VM Import/Export <https://docs.aws.amazon.com/vm-import/latest/userguide/vmexport_image.html>`__ in the *VM Import/Export User Guide*.

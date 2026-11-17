**To get details for a particular job**

The following ``get-job`` example requests the information for the job with ID ``1234567890987-1ab2c3``, which in this example ended in an error. ::

    aws mediaconvert get-job \
        --endpoint-url https://abcd1234.mediaconvert.region-name-1.amazonaws.com \
        --id 1234567890987-1ab2c3

To get your account-specific endpoint, use ``describe-endpoints``, or send the command without the endpoint. The service returns an error and your endpoint.

If your request is successful, the service returns a JSON file with job information, including job settings, any returned errors, and other job data.

Output::

    {
        "Job": {
            "Status": "ERROR",
            "Queue": "arn:aws:mediaconvert:region-name-1:123456789012:queues/Queue1",
            "Settings": {
                "Inputs": [
                    {
                        "FileInput": "s3://amzn-s3-demo-bucket/file-name.mp4"
                    }
                ],
                "OutputGroups": [
                    {
                        "Name": "File Group",
                        "OutputGroupSettings": {
                            "Type": "FILE_GROUP_SETTINGS",
                            "FileGroupSettings": {
                                "Destination": "s3://amzn-s3-demo-bucket/output/"
                            }
                        },
                        "Outputs": [
                            {
                                "Extension": "mp4",
                                "NameModifier": "_720p",
                                "Preset": "System-Generic_Hd_Mp4_Avc_Aac_16x9_Sdr_1280x720p_30Hz_5Mbps_Qvbr_Vq9"
                            }
                        ]
                    }
                ]
            },
            "ErrorMessage": "Unable to open input file [s3://amzn-s3-demo-bucket/file-name.mp4]: [Failed probe/open: [Failed to read data: AssumeRole failed]]",
            "ErrorCode": 1434,
            "Role": "arn:aws:iam::123456789012:role/MediaConvertServiceRole",
            "Arn": "arn:aws:mediaconvert:us-west-2:123456789012:jobs/1234567890987-1ab2c3",
            "UserMetadata": {},
            "Timing": {
                "FinishTime": 1517442131,
                "SubmitTime": 1517442103,
                "StartTime": 1517442104
            },
            "Id": "1234567890987-1ab2c3",
            "CreatedAt": 1517442103
        }
    }

For more information, see `Working with jobs <https://docs.aws.amazon.com/mediaconvert/latest/ug/working-with-jobs.html>`__ in the *AWS Elemental MediaConvert User Guide*.

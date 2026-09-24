**To view the details of a specified notification event**

The following ``get-notification-event`` example displays a specific notification event. ::

    aws notifications get-notification-event \
        --arn arn:aws:notifications:us-east-1:123456789012:configuration/a01jg2z8xtb12whwyg3ztxmjazh/event/a01jjta9p8wvpgt281q0e10e457

Output::

    {
        "arn": "arn:aws:notifications:us-east-1:123456789012:configuration/a01jg2z8xtb12whwyg3ztxmjazh/event/a01jjta9p8wvpgt281q0e10e457",
        "notificationConfigurationArn": "arn:aws:notifications::123456789012:configuration/a01jg2z8xtb12whwyg3ztxmjazh",
        "creationTime": "2024-11-30T00:38:09.948000+00:00",
        "content": {
            "schemaVersion": "v1.0",
            "id": "a01jjta9p8wvpgt281q0e10e457",
            "sourceEventMetadata": {
                "eventTypeVersion": "0",
                "sourceEventId": "0c1aa45d-8e0c-6a46-114c-f89a9f7c3bd1",
                "eventOriginRegion": "us-east-1",
                "relatedAccount": "123456789012",
                "source": "aws.health",
                "eventOccurrenceTime": "2024-11-30T00:37:40+00:00",
                "eventType": "AWS Health Event",
                "relatedResources": []
            },
            "messageComponents": {
                "headline": "$SingleSentenceSummary",
                "paragraphSummary": "$ParagraphSummary",
                "completeDescription": "$CompleteDescription",
                "dimensions": [
                    {
                        "name": "Affected account",
                        "value": "123456789012"
                    },
                    {
                        "name": "Service",
                        "value": "CLOUDFRONT"
                    },
                    {
                        "name": "Event type code",
                        "value": "AWS_CLOUDFRONT_OPERATIONAL_ISSUE"
                    },
                    {
                        "name": "Event type category",
                        "value": "issue"
                    },
                    {
                        "name": "Event region",
                        "value": "global"
                    },
                    {
                        "name": "Start time",
                        "value": "Wed, 29 Nov 2024 10:18:05 GMT"
                    },
                    {
                        "name": "End time",
                        "value": "Wed, 29 Nov 2024 11:40:53 GMT"
                    }
                ]
            },
            "sourceEventDetailUrl": "https://health.aws.amazon.com/health/home?region=us-east-1#/event-log?eventID=arn:aws:health:global::event/CLOUDFRONT/AWS_CLOUDFRONT_OPERATIONAL_ISSUE/AWS_CLOUDFRONT_OPERATIONAL_ISSUE_94265_0AFCF3D5C81&eventTab=details&layout=vertical",
            "notificationType": "ALERT",
            "aggregationEventType": "NONE",
            "textParts": {
                "CompleteDescription": {
                    "type": "LOCALIZED_TEXT",
                    "textByLocale": {
                        "en_US": "Current severity level: Operating normally\n\n[RESOLVED] Increased Error Rates\n\n[03:40 AM PST] Between November 28 10:56 PM and November 29 3:06 AM PST, we experienced an issue for CloudFront customers with S3 static website origins. This issue was the result of a recent change which impacted traffic from certain CloudFront locations to S3 static website origins and resulted in \"404 NoSuchBucket\" errors. Our engineers were engaged and immediately began investigating multiple parallel paths to mitigate the impact. We initiated a rollback of the change which led to full recovery of errors at 3:06 AM PST. The issue has been resolved and the service is operating normally."
                    }
                },
                "ParagraphSummary": {
                    "type": "LOCALIZED_TEXT",
                    "textByLocale": {
                        "en_US": "Current severity level: Operating normally\n\n[RESOLVED] Increased Error Rates\n\n[03:40 AM PST] Between November 28 10:56 PM and November 29 3:06 AM PST, we experienced an issue for CloudFront customers with S3 static website origins. This issue was the result of a recent change which impacted traffic from certain CloudFront locations to S3 static website origins and resulted in \"404 NoSuchBucket\" errors. Our engineers were engaged and immediately began investigating multiple parallel paths to mitigate the im..."
                    }
                },
                "SingleSentenceSummary": {
                    "type": "LOCALIZED_TEXT",
                    "textByLocale": {
                        "en_US": "Health Event: AWS CLOUDFRONT OPERATIONAL ISSUE in global on account 123456789012."
                    }
                }
            },
            "media": []
        }
    }
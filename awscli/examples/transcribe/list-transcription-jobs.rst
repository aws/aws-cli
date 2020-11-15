**To list your transcription jobs**

The following ``list-transcription-jobs`` example lists the transcription jobs associated with your AWS account and Region. ::

    aws transcribe list-transcription-jobs

Output::

    {
        "NextToken": "3/Q22yZ4n/FldYqPp93OxJf+3XU2rPiLLq65acAo3UGeSn9C1j6ZnHqRrN5HC8FWQ8OToBM443mN2ZcSO+h7XSO1mMPKFipI7QZ9wY0qkFKLSlfqofUl6BShbz7b/T7oZZTG+MtFdhNTnIiLRLtAQRDM4owpJt7ao4UXbQ9Zi4zMx0c9b+hPZZI1lmcIPHS66Spye7bwd5/IO9DCDFww+xE/LXoVlzGtXBvDRJfbG+K0P52yc73Z4WEle3f4CuwSmPutAWTKdLzPpuf8mOoKdjY9MW+KAvm6kpjeIN5JgTY7EJO3FPi+ezHrSgEFrfSglwK8FEX2AawwG/iPFSxvn9+fdSAPaWfW0yxDo8Z4VJd2GS9A4vsyzms1UXiRqkyVFMbrsmL7OjL3PlRZnT/MhqsgtpIZDU9Keb+9enaWsaLwovaHJc62Q7P9MwhqGgLjwRZuQS/BT2IQ7LkQioxVPS2Z3YYP1rMHYUtorfFcZF9ZCdca9IJ3Z+Rrvu7bVAOxmepJGDWKpDCNOigWCYAC1MWL2sHy57rNRHstZMz36+fgXxa7T25Wg5OX1hcm3Uk/bpIsHCHVMMLyjJxJtuknKtCtsLokBVQisNBWdlerjXcOttUxKVYIxJ4Tf7rOSp7JYOwASm7WPoNWJsNywPKjjTCftBYC6+BuFZ2kusnDwIsrYpM6/QMH2WnO77ka8fOAd7bSLdBpnFv+NtUz7+3uEYiLuuLf6nBk+sK0evfBOf1LCfscyluobaOevz/+WAsjEJ64fV8wcVTD+1fIGOXnG0rVwBZpQdAOy9k8IHubV2sSax+0sqR05gv7IYiYM9YjMerRy4CjMZidwtwmKElzPczq2qscYcXdjx/CFXi7/y0MXG1iA=",
        "TranscriptionJobSummaries": [
            {
                "TranscriptionJobName": "speak-id-job-1",
                "CreationTime": "2020-08-17T21:06:15.391000+00:00",
                "StartTime": "2020-08-17T21:06:15.416000+00:00",
                "CompletionTime": "2020-08-17T21:07:05.098000+00:00",
                "LanguageCode": "en-US",
                "TranscriptionJobStatus": "COMPLETED",
                "OutputLocationType": "SERVICE_BUCKET"
            },
            {
                "TranscriptionJobName": "job-1",
                "CreationTime": "2020-08-17T20:50:24.207000+00:00",
                "StartTime": "2020-08-17T20:50:24.230000+00:00",
                "CompletionTime": "2020-08-17T20:52:18.737000+00:00",
                "LanguageCode": "en-US",
                "TranscriptionJobStatus": "COMPLETED",
                "OutputLocationType": "SERVICE_BUCKET"
            },
            {
                "TranscriptionJobName": "sdk-test-job-4",
                "CreationTime": "2020-08-17T20:32:27.917000+00:00",
                "StartTime": "2020-08-17T20:32:27.956000+00:00",
                "CompletionTime": "2020-08-17T20:33:15.126000+00:00",
                "LanguageCode": "en-US",
                "TranscriptionJobStatus": "COMPLETED",
                "OutputLocationType": "SERVICE_BUCKET"
            },
            {
                "TranscriptionJobName": "Diarization-speak-id",
                "CreationTime": "2020-08-10T22:10:09.066000+00:00",
                "StartTime": "2020-08-10T22:10:09.116000+00:00",
                "CompletionTime": "2020-08-10T22:26:48.172000+00:00",
                "LanguageCode": "en-US",
                "TranscriptionJobStatus": "COMPLETED",
                "OutputLocationType": "SERVICE_BUCKET"
            },
            {
                "TranscriptionJobName": "your-transcription-job-name",
                "CreationTime": "2020-07-29T17:45:09.791000+00:00",
                "StartTime": "2020-07-29T17:45:09.826000+00:00",
                "CompletionTime": "2020-07-29T17:46:20.831000+00:00",
                "LanguageCode": "en-US",
                "TranscriptionJobStatus": "COMPLETED",
                "OutputLocationType": "SERVICE_BUCKET"
            }
        ]
    }

For more information, see `Getting Started (AWS Command Line Interface) <https://docs.aws.amazon.com/transcribe/latest/dg/getting-started-cli.html>`__ in the *Amazon Transcribe Developer Guide*.
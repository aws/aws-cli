**To list your lexicons**

The following ``list-lexicons`` example lists your pronunciation lexicons. ::

    aws polly list-lexicons

Output::

    {
        "Lexicons": [
            {
                "Name": "w3c",
                "Attributes": {
                    "Alphabet": "ipa",
                    "LanguageCode": "en-US",
                    "LastModified": 1603908910.99,
                    "LexiconArn": "arn:aws:polly:us-west-2:123456789012:lexicon/w3c",
                    "LexemesCount": 1,
                    "Size": 492
                }
            }
        ]
    }

For more information, see `Managing lexicons <https://docs.aws.amazon.com/polly/latest/dg/managing-lexicons.html>`__ in the *Amazon Polly Developer Guide*.

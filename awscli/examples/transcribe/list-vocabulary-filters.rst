**To list your vocabulary filters**

The following ``list-vocabulary-filters`` example lists the vocabulary filters associated with your AWS account and Region. ::

    aws transcribe list-vocabulary-filters

Output::

    {
        "NextToken": "3/PblzkiGhzjER3KHuQt2fmbPLF7cDYafjFMEoGn44ON/gsuUSTIkGyanvRE6WMXFd/ZTEc2EZj+P9eii/z1O2FDYli6RLI0WoRX4RwMisVrh9G0Kie0Y8ikBCdtqlZB10Wa9McC+ebOl+LaDtZPC4u1fkmh8CxJgHjDlWqBB8cTO1Sk+V6cYZDyqUkdUI6NJGmhhz74PEDlywYgZisdj9QdsNIz0G6D2xE3YDke4KXbq6fmlP8DUDixk7uJPctVm0T3qNMtpJEH/tXz6xa1PTzTTnFD7E1nSqDLXXlU4mWIt58Wd2Rg/CIwAYZxgXxbg3Vbn5YDZR2pdgHTjIKEeFU1F4WAIwLKRJWuJj9/6pxynBnp0bVZlM3UNQcxL1+ZzOELOUbooHv1HIiSvCz8imgFQ8dxT+tnFCoFloGJgEKmX00xxaWSpGU9OUVtQm0rrntY/y78HHmjT8aY8gdfFmpbsQlGy64rEF1jHrEwnIvQ8P0cphsWd6l3gYhI0Ieb/jMs6A+66Q1VhgmIJD9sX8L25wjPgwz2pJ/u44fuis/HecqExWIENl8Zaiegkx5Cpa4tf4+OzN9VUVuipPNzt0jGP1szyA313b77C76/jtrNE=",
        "VocabularyFilters": [
            {
                "VocabularyFilterName": "testFilter",
                "LanguageCode": "en-US",
                "LastModifiedTime": "2020-05-07T22:39:32.147000+00:00"
            },
            {
                "VocabularyFilterName": "monkey-filter",
                "LanguageCode": "en-US",
                "LastModifiedTime": "2020-05-21T23:29:35.174000+00:00"
            },
            {
                "VocabularyFilterName": "filter2",
                "LanguageCode": "en-US",
                "LastModifiedTime": "2020-05-08T20:18:26.426000+00:00"
            },
            {
                "VocabularyFilterName": "filter-review",
                "LanguageCode": "en-US",
                "LastModifiedTime": "2020-06-03T18:52:30.448000+00:00"
            },
            {
                "VocabularyFilterName": "crlf-filt",
                "LanguageCode": "en-US",
                "LastModifiedTime": "2020-05-22T19:42:42.737000+00:00"
            }
        ]
    }

For more information, see `Filtering Unwanted Words <https://docs.aws.amazon.com/transcribe/latest/dg/filter-unwanted-words.html>`__ in the *Amazon Transcribe Developer Guide*.
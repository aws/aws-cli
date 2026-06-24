**To list supported languages**

The following ``list-languages`` example lists all languages supported by Amazon Translate. ::

    aws translate list-languages

Output::

    {
        "Languages": [
            {
                "LanguageName": "Afrikaans",
                "LanguageCode": "af"
            },
            {
                "LanguageName": "Albanian",
                "LanguageCode": "sq"
            },
            {
                "LanguageName": "Amharic",
                "LanguageCode": "am"
            },
            {
                "LanguageName": "Arabic",
                "LanguageCode": "ar"
            },
            {
                "LanguageName": "Armenian",
                "LanguageCode": "hy"
            },
            {
                "LanguageName": "Azerbaijani",
                "LanguageCode": "az"
            }
        ]
    }

**To list languages with a specific display language**

The following ``list-languages`` example lists supported languages with names displayed in German. ::

    aws translate list-languages \
        --display-language-code de

Output::

    {
        "Languages": [
            {
                "LanguageName": "Afrikaans",
                "LanguageCode": "af"
            },
            {
                "LanguageName": "Albanisch",
                "LanguageCode": "sq"
            },
            {
                "LanguageName": "Amharisch",
                "LanguageCode": "am"
            }
        ]
    }

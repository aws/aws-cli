**To translate text from one language to another**

The following ``translate-text`` example translates the text "Hello, world!" from English to Spanish. ::

    aws translate translate-text \
        --source-language-code en \
        --target-language-code es \
        --text "Hello, world!"

Output::

    {
        "TranslatedText": "¡Hola, mundo!",
        "SourceLanguageCode": "en",
        "TargetLanguageCode": "es"
    }

**To translate text with auto-detection of source language**

The following ``translate-text`` example translates text without specifying the source language, allowing Amazon Translate to automatically detect it. ::

    aws translate translate-text \
        --source-language-code auto \
        --target-language-code fr \
        --text "Good morning"

Output::

    {
        "TranslatedText": "Bonjour",
        "SourceLanguageCode": "en",
        "TargetLanguageCode": "fr"
    }

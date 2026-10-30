**To delete a medical custom vocabulary**

The following ``delete-medical-vocabulary`` example deletes a medical custom vocabulary. For vocabulary-name, specify the name of the medical custom vocabulary. ::

    aws transcribe delete-vocabulary \
        --vocabulary-name medical-custom-vocabulary-name

This command produces no output.

For more information, see `Improving transcription accuracy with medical custom vocabularies <https://docs.aws.amazon.com/transcribe/latest/dg/vocabulary-med.html>`__ in the *Amazon Transcribe Developer Guide*.
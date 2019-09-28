**To update several phone numbers at the same time**

The following ``batch-update-phone-number`` example updates the product types for all of the specified phone numbers. ::

    aws chime batch-update-phone-number \
        --update-phone-number-request-items PhoneNumberId=%2B12065550100,ProductType=BusinessCalling PhoneNumberId=%2B12065550101,ProductType=BusinessCalling

Output::

    {
        "PhoneNumberErrors": []
    }

For more information, see `Working with Phone Numbers <https://docs.aws.amazon.com/chime/latest/ag/phone-numbers.html>`__ in the *Amazon Chime Administration Guide*.

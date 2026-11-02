**To create a SAML provider**

The following ``create-saml-provider`` example creates a new SAML provider in IAM named ``MySAMLProvider``. It is described by the SAML metadata document found in the file ``SAMLMetaData.xml``. ::

    aws iam create-saml-provider \
        --saml-metadata-document file://SAMLMetaData.xml \
        --name MySAMLProvider

Contents of ``SAMLMetaData.xml``::

    <?xml version="1.0" encoding="UTF-8"?>
    <md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" entityID="https://idp.example.com/saml/metadata">
        <md:IDPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
            <md:KeyDescriptor use="signing">
                <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                    <ds:X509Data>
                        <ds:X509Certificate>MIIC8DCCAdigAwIBAgIQEXAMPLE...</ds:X509Certificate>
                    </ds:X509Data>
                </ds:KeyInfo>
            </md:KeyDescriptor>
            <md:NameIDFormat>urn:oasis:names:tc:SAML:2.0:nameid-format:persistent</md:NameIDFormat>
            <md:SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="https://idp.example.com/saml/sso"/>
        </md:IDPSSODescriptor>
    </md:EntityDescriptor>

Output::

    {
        "SAMLProviderArn": "arn:aws:iam::123456789012:saml-provider/MySAMLProvider"
    }

For more information, see `Creating IAM SAML identity providers <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_saml.html>`__ in the *AWS IAM User Guide*.
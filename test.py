import os

# Import the Google Cloud Translation library.
from google.cloud import translate_v3

PROJECT_ID = "global-axe-468209-i1"


def translate_text(
    text: str = "YOUR_TEXT_TO_TRANSLATE",
    source_language_code: str = "en-US",
    target_language_code: str = "vi",
) -> translate_v3.TranslationServiceClient:

    client = translate_v3.TranslationServiceClient()
    parent = f"projects/{PROJECT_ID}/locations/global"
    mime_type = "text/plain"

    # Translate text from the source to the target language.
    response = client.translate_text(
        contents=[text],
        parent=parent,
        mime_type=mime_type,
        source_language_code=source_language_code,
        target_language_code=target_language_code,
    )

    # Display the translation for the text.
    # For example, for "Hello! How are you doing today?":
    # Translated text: Bonjour comment vas-tu aujourd'hui?
    for translation in response.translations:
        print(f"Translated text: {translation.translated_text}")

    return response


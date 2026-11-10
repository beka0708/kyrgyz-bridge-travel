import phonenumbers
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

MISSING = "Please leave an email or a phone number so we can reply."
BAD_EMAIL = "This looks like an email, but something is off. Please check it."
BAD_PHONE = "This number looks incomplete. Check the country and the digits."


def normalize_contact(email: str, contact: str) -> tuple[str, str]:
    """Clean the two ways to reach a tourist: an email and a phone (`contact`); one is enough.

    - an email typed into the phone field (old form, no JavaScript) is moved to `email`;
    - an international number (+…, as the country picker sends it) is checked and stored as
      +996 704 313 147. Numbers without a country code are kept as typed.
    Returns (email, contact). Raises ValidationError with the message for the `contact` field.
    """
    email, contact = (email or "").strip(), (contact or "").strip()
    if not email and "@" in contact:
        try:
            validate_email(contact)
        except ValidationError:
            raise ValidationError(BAD_EMAIL) from None
        email, contact = contact, ""
    if contact.startswith("+"):
        try:
            number = phonenumbers.parse(contact, None)
        except phonenumbers.NumberParseException:
            raise ValidationError(BAD_PHONE) from None
        if not phonenumbers.is_valid_number(number):
            raise ValidationError(BAD_PHONE)
        contact = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    if not email and not contact:
        raise ValidationError(MISSING)
    return email, contact

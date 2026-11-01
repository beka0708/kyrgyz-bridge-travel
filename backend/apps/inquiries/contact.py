from django.core.exceptions import ValidationError
from django.core.validators import validate_email

MISSING = "Please leave an email or a WhatsApp number so we can reply."
BAD_EMAIL = "This looks like an email, but something is off. Please check it."


def normalize_contact(email: str, contact: str) -> tuple[str, str]:
    """The form has one «Email or WhatsApp» field (`contact`): move an email into `email`.

    Returns (email, contact). Raises ValidationError with the message for the `contact` field.
    """
    email, contact = (email or "").strip(), (contact or "").strip()
    if not email and "@" in contact:
        try:
            validate_email(contact)
        except ValidationError:
            raise ValidationError(BAD_EMAIL) from None
        email, contact = contact, ""
    if not email and not contact:
        raise ValidationError(MISSING)
    return email, contact

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired, FileSize
from wtforms import (BooleanField, EmailField, PasswordField, SelectField, StringField, SubmitField,
                     TextAreaField, URLField)
from wtforms.validators import Email, InputRequired, Length, Optional, URL

# ------------------------------------------------------------------------------------------------------
# Field Lengths
# ------------------------------------------------------------------------------------------------------
NAME_MAX_LENGTH = 100
EMAIL_MAX_LENGTH = 254
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 256
CAPTION_MAX_LENGTH = 250
ALT_TEXT_MAX_LENGTH = 150
URL_NAME_MAX_LENGTH = 20
URL_MAX_LENGTH = 2048

IMAGE_MAX_SIZE_MB = 10
THUMBNAIL_MAX_SIZE_MB = 5

# ------------------------------------------------------------------------------------------------------
# DATA REQUIRED VALIDATION
# ------------------------------------------------------------------------------------------------------
FIELD_REQUIRED = "This field is required."


def required_validators(message: str = FIELD_REQUIRED) -> list:
    return [InputRequired(message=message)]


def required_render_kw(message: str = FIELD_REQUIRED) -> dict:
    return {
        "required": True,
        "data-msg-required": message,
    }


# ------------------------------------------------------------------------------------------------------
# STRING VALIDATION
# ------------------------------------------------------------------------------------------------------
def string_validators(min_len: int = -1, max_len: int = -1, required: bool = False) -> list:
    if min_len > -1 and -1 < max_len < min_len:
        raise ValueError("`min_len` cannot be more than `max_len`.")

    validators: list = required_validators() if required else [Optional()]

    if min_len > -1:
        validators.append(Length(min=min_len, message=f"Please use at least {min_len} characters."))

    if max_len > -1:
        validators.append(Length(max=max_len, message=f"Please use {max_len} characters or fewer."))

    return validators


def string_render_kw(min_len: int = -1, max_len: int = -1, required: bool = False) -> dict:
    if min_len > -1 and -1 < max_len < min_len:
        raise ValueError("`min_len` cannot be more than `max_len`.")

    render_kw: dict = required_render_kw() if required else {}

    if min_len > -1:
        render_kw["minlength"] = min_len
        render_kw["data-msg-too-short"] = f"Please use at least {min_len} characters."

    if max_len > -1:
        render_kw["maxlength"] = max_len
        render_kw["data-msg-too-long"] = f"Please use {max_len} characters or fewer."

    return render_kw


# ------------------------------------------------------------------------------------------------------
# EMAIL VALIDATION
# ------------------------------------------------------------------------------------------------------
EMAIL_INVALID = "Please enter a valid email address."
EMAIL_TOO_LONG = f"Please use {EMAIL_MAX_LENGTH} characters or fewer."


def email_validators(required: bool = False) -> list:
    validators: list = required_validators() if required else [Optional()]

    validators.extend([
        Email(message=EMAIL_INVALID),
        Length(max=EMAIL_MAX_LENGTH, message=EMAIL_TOO_LONG),
    ])

    return validators


def email_render_kw(required: bool = False) -> dict:
    render_kw: dict = required_render_kw() if required else {}
    render_kw.update({
        "maxlength": EMAIL_MAX_LENGTH,
        "data-msg-type-mismatch": EMAIL_INVALID,
        "data-msg-too-long": EMAIL_TOO_LONG,
    })

    return render_kw


# ------------------------------------------------------------------------------------------------------
# PASSWORD VALIDATION
# ------------------------------------------------------------------------------------------------------
def password_validators(required: bool = False) -> list:
    return string_validators(PASSWORD_MIN_LENGTH, PASSWORD_MAX_LENGTH, required)


def password_render_kw(required: bool = False) -> dict:
    return string_render_kw(PASSWORD_MIN_LENGTH, PASSWORD_MAX_LENGTH, required)


# ------------------------------------------------------------------------------------------------------
# FILE VALIDATION
# ------------------------------------------------------------------------------------------------------
BYTES_PER_MB = 1024 * 1024
IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
}

IMAGE_INVALID = "Please submit a valid image."
FILE_REQUIRED = "This file is required."
FILE_TOO_LARGE = "File must be {max_size_mb}MB or smaller."


def file_validators(max_size_mb: int = -1, is_image: bool = False, required: bool = False) -> list:
    validators: list = [FileRequired(message=FILE_REQUIRED)] if required else [Optional()]

    if max_size_mb > -1:
        validators.append(
            FileSize(
                max_size=max_size_mb * BYTES_PER_MB,
                message=FILE_TOO_LARGE.format(max_size_mb=max_size_mb),
            )
        )

    if is_image:
        validators.append(
            FileAllowed(
                IMAGE_EXTENSIONS,
                message=IMAGE_INVALID,
            )
        )

    return validators


def file_render_kw(max_size_mb: int = -1, is_image: bool = False, required: bool = False) -> dict:
    render_kw: dict = required_render_kw(FILE_REQUIRED) if required else {}

    if is_image:
        render_kw["accept"] = ",".join(
            f".{extension}" for extension in IMAGE_EXTENSIONS
        )
        render_kw["data-msg-invalid-file"] = IMAGE_INVALID

    if max_size_mb > -1:
        render_kw["data-max-size-bytes"] = max_size_mb * BYTES_PER_MB
        render_kw["data-msg-file-too-large"] = FILE_TOO_LARGE.format(
            max_size_mb=max_size_mb
        )

    return render_kw


# ------------------------------------------------------------------------------------------------------
# URL VALIDATION
# ------------------------------------------------------------------------------------------------------
URL_INVALID = "Please enter a valid url."
URL_TOO_LONG = f"Please use {URL_MAX_LENGTH} characters or fewer."


def url_validators(required: bool = False) -> list:
    validators: list = required_validators() if required else [Optional()]

    validators.extend([
        URL(message=URL_INVALID),
        Length(max=URL_MAX_LENGTH, message=URL_TOO_LONG),
    ])

    return validators


def url_render_kw(required: bool = False) -> dict:
    render_kw: dict = required_render_kw() if required else {}

    render_kw.update({
        "maxlength": URL_MAX_LENGTH,
        "data-msg-type-mismatch": URL_INVALID,
        "data-msg-too-long": URL_TOO_LONG,
    })

    return render_kw


# Create a form to contact me
class ContactForm(FlaskForm):
    name = StringField(
        "Company/Name",
        validators=string_validators(max_len=NAME_MAX_LENGTH, required=True),
        render_kw=string_render_kw(max_len=NAME_MAX_LENGTH, required=True),
    )
    email = EmailField(
        "Email",
        validators=email_validators(True),
        render_kw=email_render_kw(True),
    )
    reason = SelectField(
        "Reason",
        choices=[("questions", "Questions"), ("project", "Project"), ("consultation", "Consultation"),
                 ("collab", "Collab"), ("hire", "Hire"), ("support", "Support"), ("other", "Other")],
        validators=required_validators(),
        render_kw=required_render_kw(),
    )
    message = TextAreaField(
        "Message",
        validators=required_validators(),
        render_kw=required_render_kw(),
    )
    send_copy = BooleanField("Send a copy to yourself")
    submit = SubmitField("Submit")


# Create a form to register/edit admins
class RegisterAdminForm(FlaskForm):
    name = StringField(
        "Name",
        validators=string_validators(max_len=NAME_MAX_LENGTH, required=True),
        render_kw=string_render_kw(max_len=NAME_MAX_LENGTH, required=True),
    )
    email = EmailField(
        "Email",
        validators=email_validators(True),
        render_kw=email_render_kw(True),
    )
    password = PasswordField(
        "Password",
        validators=password_validators(True),
        render_kw=password_render_kw(True),
    )
    submit = SubmitField("Register")


# Create a form to login existing admins
class LoginAdminForm(FlaskForm):
    email = EmailField(
        "Email",
        validators=email_validators(True),
        render_kw=email_render_kw(True),
    )
    password = PasswordField(
        "Password",
        validators=password_validators(True),
        render_kw=password_render_kw(True),
    )
    submit = SubmitField("Login")


# Create a form to register/edit admins
class EditAdminForm(FlaskForm):
    name = StringField(
        "Name",
        validators=string_validators(max_len=NAME_MAX_LENGTH, required=True),
        render_kw=string_render_kw(max_len=NAME_MAX_LENGTH, required=True),
    )
    email = EmailField(
        "Email",
        validators=email_validators(True),
        render_kw=email_render_kw(True),
    )
    password = PasswordField(
        "Password",
        validators=password_validators(),
        render_kw=password_render_kw(),
    )
    submit = SubmitField("Submit")


# Create a form to add projects
class AddProjectForm(FlaskForm):
    title = StringField(
        "Title",
        validators=string_validators(max_len=NAME_MAX_LENGTH, required=True),
        render_kw=string_render_kw(max_len=NAME_MAX_LENGTH, required=True),
    )
    category = SelectField(
        "Category",
        choices=[("Backend", "Backend"), ("Frontend", "Frontend"), ("3D Art", "3D Art")],
        validators=required_validators(),
        render_kw=required_render_kw(),
    )
    caption = StringField(
        "Caption",
        validators=string_validators(max_len=CAPTION_MAX_LENGTH, required=True),
        render_kw=string_render_kw(max_len=CAPTION_MAX_LENGTH, required=True),
    )
    image = FileField(
        "Image",
        validators=file_validators(max_size_mb=IMAGE_MAX_SIZE_MB, is_image=True, required=True),
        render_kw=file_render_kw(max_size_mb=IMAGE_MAX_SIZE_MB, is_image=True, required=True),
    )
    thumbnail = FileField(
        "Thumbnail",
        validators=file_validators(max_size_mb=THUMBNAIL_MAX_SIZE_MB, is_image=True, required=True),
        render_kw=file_render_kw(max_size_mb=THUMBNAIL_MAX_SIZE_MB, is_image=True, required=True),
    )
    thumbnail_alt = StringField(
        "Alt Text",
        validators=string_validators(max_len=ALT_TEXT_MAX_LENGTH, required=True),
        render_kw=string_render_kw(max_len=ALT_TEXT_MAX_LENGTH, required=True),
    )
    url_name = StringField(
        "URL Name",
        validators=string_validators(max_len=URL_NAME_MAX_LENGTH, required=True),
        render_kw=string_render_kw(max_len=URL_NAME_MAX_LENGTH, required=True),
    )
    url = URLField(
        "URL",
        validators=url_validators(True),
        render_kw=url_render_kw(True),
    )
    submit = SubmitField("Submit")


# Create a form to edit projects
class EditProjectForm(FlaskForm):
    title = StringField(
        "Title",
        validators=string_validators(max_len=NAME_MAX_LENGTH, required=True),
        render_kw=string_render_kw(max_len=NAME_MAX_LENGTH, required=True),
    )
    category = SelectField(
        "Category",
        choices=[("Backend", "Backend"), ("Frontend", "Frontend"), ("3D Art", "3D Art")],
        validators=required_validators(),
        render_kw=required_render_kw(),
    )
    caption = StringField(
        "Caption",
        validators=string_validators(max_len=CAPTION_MAX_LENGTH, required=True),
        render_kw=string_render_kw(max_len=CAPTION_MAX_LENGTH, required=True),
    )
    image = FileField(
        "Image",
        validators=file_validators(max_size_mb=IMAGE_MAX_SIZE_MB, is_image=True),
        render_kw=file_render_kw(max_size_mb=IMAGE_MAX_SIZE_MB, is_image=True),
    )
    thumbnail = FileField(
        "Thumbnail",
        validators=file_validators(max_size_mb=THUMBNAIL_MAX_SIZE_MB, is_image=True),
        render_kw=file_render_kw(max_size_mb=THUMBNAIL_MAX_SIZE_MB, is_image=True),
    )
    thumbnail_alt = StringField(
        "Alt Text",
        validators=string_validators(max_len=ALT_TEXT_MAX_LENGTH, required=True),
        render_kw=string_render_kw(max_len=ALT_TEXT_MAX_LENGTH, required=True),
    )
    url_name = StringField(
        "URL Name",
        validators=string_validators(max_len=URL_NAME_MAX_LENGTH, required=True),
        render_kw=string_render_kw(max_len=URL_NAME_MAX_LENGTH, required=True),
    )
    url = URLField(
        "URL",
        validators=url_validators(True),
        render_kw=url_render_kw(True),
    )
    submit = SubmitField("Submit")

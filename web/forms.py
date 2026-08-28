from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired, FileSize
from wtforms import BooleanField, EmailField, PasswordField, SelectField, StringField, SubmitField, TextAreaField, \
    URLField
from wtforms.validators import DataRequired, Email, Length, URL

EMAIL_VALIDATORS = [DataRequired(), Email(), Length(max=254)]
IMAGE_VALIDATOR = FileAllowed(["jpg", "png", "jpeg", "gif", "webp"], "Images only!")
PASSWORD_VALIDATORS = [DataRequired(), Length(max=256)]
LINK_VALIDATORS = [DataRequired(), Length(max=2048), URL()]
IMAGE_MAX = 10 * (1024 * 1024)
THUMB_MAX = 5 * (1024 * 1024)


# Create a form to contact me
class ContactForm(FlaskForm):
    name = StringField("Company/Name", validators=[DataRequired(), Length(max=100)])
    email = EmailField("Email", validators=EMAIL_VALIDATORS)
    reason = SelectField("Reason",
                         choices=[("questions", "Questions"), ("project", "Project"), ("consultation", "Consultation"),
                                  ("collab", "Collab"), ("hire", "Hire"), ("support", "Support"), ("other", "Other")],
                         validators=[DataRequired()])
    message = TextAreaField("Message", validators=[DataRequired()])
    send_copy = BooleanField("Send copy")
    submit = SubmitField("Submit")


# Create a form to login existing admins
class LoginForm(FlaskForm):
    email = StringField("Email", validators=EMAIL_VALIDATORS)
    password = PasswordField("Password", validators=PASSWORD_VALIDATORS)
    submit = SubmitField("Login")


# Create a form to add projects
class AddProjectForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=100)])
    category = SelectField("Category",
                           choices=[("Backend", "Backend"), ("Frontend", "Frontend"), ("3D Art", "3D Art")],
                           validators=[DataRequired()])
    caption = StringField("Caption", validators=[DataRequired(), Length(max=250)])
    image = FileField("Image", validators=[
        FileRequired(message="Image file required."),
        FileSize(max_size=IMAGE_MAX, message="Maximum image size is 10MB."),
        IMAGE_VALIDATOR
    ])
    thumbnail = FileField("Thumbnail", validators=[
        FileRequired(message="Image file required."),
        FileSize(max_size=THUMB_MAX, message="Maximum thumbnail size is 5MB."),
        IMAGE_VALIDATOR
    ])
    thumbnail_alt = StringField("Alt Text", validators=[Length(max=100)])
    url_name = StringField("URL Name", validators=[DataRequired(), Length(max=20)])
    url = URLField("URL", validators=LINK_VALIDATORS)
    submit = SubmitField("Submit")


# Create a form to edit projects
class EditProjectForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=100)])
    category = SelectField("Category",
                           choices=[("Backend", "Backend"), ("Frontend", "Frontend"), ("3D Art", "3D Art")],
                           validators=[DataRequired()])
    caption = StringField("Caption", validators=[DataRequired(), Length(max=250)])
    image = FileField("Image", validators=[
        FileSize(max_size=IMAGE_MAX, message="Maximum image size is 10MB."),
        IMAGE_VALIDATOR
    ])
    thumbnail = FileField("Thumbnail", validators=[
        FileSize(max_size=THUMB_MAX, message="Maximum thumbnail size is 5MB."),
        IMAGE_VALIDATOR
    ])
    thumbnail_alt = StringField("Alt Text", validators=[Length(max=100)])
    url_name = StringField("URL Name", validators=[DataRequired(), Length(max=20)])
    url = URLField("URL", validators=LINK_VALIDATORS)
    submit = SubmitField("Submit")


# Create a form to register new admins
class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=EMAIL_VALIDATORS)
    password = PasswordField("Password", validators=PASSWORD_VALIDATORS)
    submit = SubmitField("Register")

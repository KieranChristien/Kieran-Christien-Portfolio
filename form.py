from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, EmailField, BooleanField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email

class ContactForm(FlaskForm):
    name = StringField("Company/Name", validators=[DataRequired()])
    email = EmailField("Email", validators=[DataRequired(), Email()])
    reason = SelectField("Reason", choices=[("questions", "Questions"), ("project", "Project"), ("consultation", "Consultation"), ("collab", "Collab"), ("hire", "Hire"), ("support", "Support"), ("other", "Other")] , validators=[DataRequired()])
    message = TextAreaField("Message", validators=[DataRequired()])
    send_copy = BooleanField("Send copy")
    submit = SubmitField("Submit")

from flask_wtf import FlaskForm
from wtforms import SubmitField, EmailField, BooleanField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email

class ContactForm(FlaskForm):
    email = EmailField("Your email", validators=[DataRequired(), Email()])
    reason = SelectField("Reason", choices=[("questions", "Questions"), ("report", "Report"), ("others", "Others")] , validators=[DataRequired()])
    message = TextAreaField("Message", validators=[DataRequired()])
    send_copy = BooleanField("Send copy")
    submit = SubmitField("Submit")

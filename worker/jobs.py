from email_form import EmailForm


def send_email_job(name, email, reason, message, send_copy):
    try:
        email = EmailForm(name, email, reason, message, send_copy)
        email.send()
    except Exception as e:
        print("Error sending email", e)
        raise
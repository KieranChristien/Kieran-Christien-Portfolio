from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import current_user

from web.email_form import EmailForm
from web.extensions import db, limiter
from web.models import Project
from web.forms import ContactForm

main = Blueprint('main', __name__)

@main.route('/')
def home():
    projects = db.session.execute(db.select(Project)).scalars().all()

    return render_template(
        'index.html',
        projects=projects,
        current_user=current_user
    )

@main.route('/contact', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        email = EmailForm(
            form.name.data,
            form.email.data,
            form.reason.data,
            form.message.data,
            form.send_copy.data,
        )

        # Send email
        err_flash, err_log = email.send()
        if err_log or err_flash:
            if err_log: current_app.logger.error(err_log)
            if err_flash: flash(err_flash, "error")
            return render_template('contact.html', form=form)

        current_app.logger.info("Sent email from %s.", form.email.data)
        flash("Email sent successfully.", "success")
        return redirect(url_for('main.contact'), 303)
    return render_template('contact.html', form=form)
from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import current_user

from web.extensions import db, limiter
from web.forms import ContactForm
from web.models import Project
from web.services.mailjet import send_email

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
        # Send email
        err = send_email(
            form.name.data,
            form.email.data,
            form.reason.data,
            form.message.data,
            form.send_copy.data,
        )
        if err:
            current_app.logger.error(err)
            flash("Email failed to send.", "error")
            return render_template('contact.html', form=form)

        current_app.logger.info("Sent email from %s.", form.email.data)
        flash("Email sent successfully.", "success")
        return redirect(url_for('main.contact'), 303)
    return render_template('contact.html', form=form)

from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for
from flask_bootstrap import Bootstrap
from form import ContactForm
from rq import Queue
import os
import redis

load_dotenv()
env = os.environ

app = Flask(__name__)
app.config['SECRET_KEY'] = env.get('SECRET_KEY')
Bootstrap(app)

redis_connection = redis.from_url(env.get('REDIS_URL'))
q = Queue("emails", connection=redis_connection)

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        reason = form.reason.data
        message = form.message.data
        send_copy = form.send_copy.data

        q.enqueue("worker.jobs.send_mail_job", name, email, reason, message, send_copy)

        return redirect(url_for('home'), 202)
    return render_template('contact.html', form=form)


if __name__ == '__main__':
    port = int(env.get('PORT', 5000))
    app.run(debug=True, host="0.0.0.0", port=port)

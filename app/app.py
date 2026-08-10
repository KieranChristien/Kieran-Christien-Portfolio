from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from email_form import EmailForm
from flask import Flask, render_template, redirect, url_for
from flask_bootstrap import Bootstrap
from form import ContactForm
import os

load_dotenv()
env = os.environ

app = Flask(__name__)
app.config['SECRET_KEY'] = env.get('SECRET_KEY')
Bootstrap(app)

_executor = ThreadPoolExecutor(max_workers=4)

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/contact', methods=['GET', 'POST'])
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

        _executor.submit(email.send)

        return redirect(url_for('home'), 303)
    return render_template('contact.html', form=form)


if __name__ == '__main__':
    port = int(env.get('PORT', 5000))
    app.run(debug=True, host="0.0.0.0", port=port)

import click
from werkzeug.security import generate_password_hash

from web.extensions import db
from web.models import Admin


def register_cli_commands(app):

    @app.cli.command("create-owner")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt=True, default="Admin")
    @click.option(
        "--password",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
    )
    def create_owner(email, name, password):
        """Create the initial owner account."""

        existing = db.session.execute(
            db.select(Admin).where(
                Admin.email == email
            )
        ).scalar_one_or_none()

        if existing:
            raise click.ClickException(
                f"An account already exists for {email}."
            )

        admin = Admin(
            email=email,
            name=name,
            password=generate_password_hash(
                password,
                method="pbkdf2:sha256",
                salt_length=16,
            ),
        )

        db.session.add(admin)
        db.session.commit()

        click.echo(
            f"Owner account created for {admin.email}."
        )
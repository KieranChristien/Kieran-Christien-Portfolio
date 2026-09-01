from flask import current_app
from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, Integer, String
from werkzeug.security import generate_password_hash

from web.extensions import db


# Create an Admin table for all registered administrators
class Admin(UserMixin, db.Model):
    __tablename__ = "admins"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(256), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_owner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# Create a Project table for recent projects
class Project(db.Model):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(15), nullable=False)
    caption: Mapped[str] = mapped_column(String(250), nullable=False)
    image: Mapped[str] = mapped_column(String(2048), nullable=False)
    image_id: Mapped[str] = mapped_column(String(2048), nullable=False)
    image_width: Mapped[int] = mapped_column(Integer, nullable=False)
    image_height: Mapped[int] = mapped_column(Integer, nullable=False)
    thumbnail_1x: Mapped[str] = mapped_column(String(2048), nullable=False)
    thumbnail_2x: Mapped[str] = mapped_column(String(2048), nullable=False)
    thumbnail_alt: Mapped[str] = mapped_column(String(100), nullable=False)
    thumbnail_id: Mapped[str] = mapped_column(String(2048), nullable=False)
    url_name: Mapped[str] = mapped_column(String(20), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)


def ensure_owner():
    owner_email = current_app.config.get("OWNER_EMAIL", "").strip().lower()
    if not owner_email:
        return

    existing_owner = db.session.execute(
        db.select(Admin).where(
            Admin.email == owner_email
        )
    ).scalar_one_or_none()

    if existing_owner:
        if existing_owner.is_owner:
            return

        existing_owner.is_owner = True
        db.session.commit()
        return

    owner = Admin()
    owner.email = owner_email
    owner.name = current_app.config["OWNER_NAME"]
    owner.password = generate_password_hash(
        current_app.config["OWNER_PASSWORD"],
        method="pbkdf2:sha256",
        salt_length=16
    )
    owner.is_owner = True

    db.session.add(owner)
    db.session.commit()

import os
from flask import current_app
from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String
from werkzeug.security import generate_password_hash

from web.extensions import db


# Create an Admin table for all registered administrators
class Admin(UserMixin, db.Model):
    __tablename__ = "admins"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(256), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


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
    email = os.environ.get("OWNER_EMAIL")
    if not email:
        return

    existing = db.session.execute(
        db.select(Admin).where(
            Admin.email == email
        )
    ).scalar_one_or_none()

    if existing:
        return

    admin = Admin(
        email=email,
        name=os.environ.get("OWNER_NAME"),
        password=generate_password_hash(os.environ.get("OWNER_PASSWORD"), method="pbkdf2:sha256", salt_length=16),
    )

    db.session.add(admin)
    db.session.commit()

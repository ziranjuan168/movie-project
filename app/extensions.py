from __future__ import annotations

from flask import Flask
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship as sa_relationship, scoped_session, sessionmaker


class Database:
    Model = declarative_base()
    session = scoped_session(sessionmaker())
    Column = Column
    Integer = Integer
    String = String
    Float = Float
    Boolean = Boolean
    DateTime = DateTime
    Text = Text
    ForeignKey = ForeignKey
    UniqueConstraint = UniqueConstraint
    def __init__(self) -> None:
        self.engine = None

    @staticmethod
    def relationship(*args, **kwargs):
        return sa_relationship(*args, **kwargs)

    def init_app(self, app: Flask) -> None:
        uri = app.config["SQLALCHEMY_DATABASE_URI"]
        connect_args = {}
        if uri.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        self.engine = create_engine(uri, future=True, connect_args=connect_args)
        self.session.remove()
        self.session.configure(bind=self.engine)
        self.Model.metadata.bind = self.engine

        @app.teardown_appcontext
        def cleanup_session(exception=None) -> None:
            self.session.remove()

    def create_all(self) -> None:
        if self.engine is None:
            raise RuntimeError("Database engine is not initialized.")
        self.Model.metadata.create_all(bind=self.engine, checkfirst=True)


db = Database()

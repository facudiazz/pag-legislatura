from sqlalchemy import create_engine, Column, Integer, String, LargeBinary, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class AdminUser(Base):
    __tablename__ = 'admin_users'
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Attachment(Base):
    __tablename__ = 'attachments'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    data = Column(LargeBinary, nullable=False)
    file_id = Column(Integer, ForeignKey('files.id'))
    file = relationship('File', back_populates='attachments')

class File(Base):
    __tablename__ = 'files'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    data = Column(LargeBinary, nullable=False)
    category = Column(String)
    expediente = Column(String)
    autor_coautor = Column(String)
    sumario = Column(String)
    fecha_ingreso = Column(String)
    giros_posteriores = Column(String)
    antecedentes = Column(String)
    relaciones = Column(String)
    downloaded_by = Column(Integer, ForeignKey('users.id'))
    attachments = relationship('Attachment', back_populates='file')
    custom_fields = relationship('CustomField', back_populates='file')


class Events(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=False)
    
class CustomField(Base):
    __tablename__ = 'custom_fields'
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey('files.id'))
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    value = Column(String)
    file = relationship('File', back_populates='custom_fields')

engine = create_engine('sqlite:///files.db')
Base.metadata.create_all(engine)

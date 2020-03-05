import os
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from sqlalchemy.exc import SQLAlchemyError
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import StringField, PasswordField, TextAreaField, SelectField, BooleanField, SubmitField
from wtforms.fields.html5 import DateField, DateTimeLocalField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional
from flask_uploads import UploadSet, configure_uploads, patch_request_class, IMAGES
from marshmallow import fields

#Get Base directory
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

#Configuration
app.config.from_pyfile('config.cfg')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOADED_PHOTOS_DEST'] = os.path.join(basedir, 'static/uploads')

#Requrst token
safe = URLSafeTimedSerializer(os.environ.get('SECRET_KEY'))

#Query data
db = SQLAlchemy(app)

#Convert data to JSON
ma = Marshmallow(app)

#Send mail
mail = Mail(app)

#Encrypt data
bcrypt = Bcrypt(app)

#Store session
login_manager = LoginManager(app)
login_manager.login_view = 'login'

#Save image 
upload = UploadSet('photos', IMAGES)
configure_uploads(app, upload)
patch_request_class(app)


#Define Form Model
class RegisterForm(FlaskForm):
    firstname = StringField('Firstname', validators=[DataRequired(), Length(max=20)])
    lastname = StringField('Lastname', validators=[DataRequired(), Length(max=20)])
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    gender = SelectField('Gender', choices=[('M', 'Male'), ('F', 'Female')], validators=[DataRequired()])
    birthdate = DateField('Date of Birth', validators=[Optional()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=20)])
    confirm = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm, UserMixin):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=20)])
    remember = BooleanField('Remember', default=False)
    submit = SubmitField('Login')

class ProfileDetailsForm(FlaskForm):
    status = SelectField('Status', choices=[('Single', 'Single'), ('In Relationship', 'In Relationship'), ('Married', 'Married')])
    phone = StringField('Phone', validators=[Optional(), Length(min=6, max=13)])
    company = StringField('Company', validators=[Optional(), Length(min=2 ,max=20)])
    hometown = StringField('Hometown', validators=[Optional(), Length(min=2 ,max=255)])
    location = StringField('Location', validators=[Optional(), Length(max=255)])
    bio = TextAreaField('Bio', validators=[Optional()])
    submit = SubmitField('Save')

class PostForm(FlaskForm):
    title = TextAreaField('Title', validators=[Optional()])
    photo = FileField('Photo', validators=[FileAllowed(upload), Optional()])
    submit = SubmitField('Post')


#Define Data Model
postLiked = db.Table(
    'postLiked',
    db.Column('post_id', db.String(36), db.ForeignKey('tbl_post.id')),
    db.Column('user_id', db.String(36), db.ForeignKey('tbl_user.id'))
)  

postViewed = db.Table(
    'postViewed',
    db.Column('post_id', db.String(36), db.ForeignKey('tbl_post.id')),
    db.Column('user_id', db.String(36), db.ForeignKey('tbl_user.id'))
)

class tblUser(db.Model, UserMixin):
    id = db.Column(db.String(36), primary_key=True)
    firstname = db.Column(db.String(20), nullable=False)
    lastname = db.Column(db.String(20), nullable=False)
    username = db.Column(db.String(20), nullable=False)
    gender = db.Column(db.String(1), nullable=False)
    birthdate = db.Column(db.Date, nullable=True)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(60), nullable=False)
    isConfirm = db.Column(db.Boolean, default=False)
    createdOn = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship('tblPost', backref='author', lazy=True)
    profile = db.relationship('tblProfile', backref='profile', lazy=True)
    likedPost = db.relationship('tblPost', secondary=postLiked, backref='likedBy', lazy=True)
    viewedPost = db.relationship('tblPost', secondary=postViewed, backref='viewedBy', lazy=True)

class tblPost(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    title = db.Column(db.Text(), nullable=False)
    photo = db.Column(db.String(100), default='default.png')
    createdOn = db.Column(db.DateTime, default=datetime.utcnow)
    createdBy = db.Column(db.String(36), db.ForeignKey('tbl_user.id'), nullable=False)

class tblProfile(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    photo = db.Column(db.String(255), nullable=True, default='default.png')
    status = db.Column(db.String(20), nullable=True, default='Single')
    phone = db.Column(db.String(13), nullable=True, default='')
    company = db.Column(db.String(20), nullable=True, default='')
    hometown = db.Column(db.String(255), nullable=True, default='')
    location = db.Column(db.String(255), nullable=True, default='')
    bio = db.Column(db.Text(), nullable=True, default='')
    user = db.Column(db.String(36), db.ForeignKey('tbl_user.id'), nullable=False)

class tblBrand(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    brand = db.Column(db.String(20), nullable=False)
    createdOn = db.Column(db.DateTime, default=datetime.utcnow)
    createdBy = db.Column(db.String(36), db.ForeignKey('tbl_user.id'), nullable=False)
    product = db.relationship('tblDetails', backref='products', lazy=True)

class tblColor(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    color = db.Column(db.String(20), nullable=False)
    hex = db.Column(db.String(100), nullable=True, default= '')
    price = db.Column(db.Numeric(10,2), nullable=True, default=0.00)
    product = db.Column(db.String(36), db.ForeignKey('tbl_product.id'), nullable=True)

class tblProcessor(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    processor = db.Column(db.String(20), nullable=True, default='')
    dprocessor = db.relationship('tblDetails', backref='dprocessor', lazy=True)
    price = db.Column(db.Numeric(10,2), nullable=True, default=0.00)

class tblMemory(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    memory = db.Column(db.String(20), nullable=True, default='')
    dmemory = db.relationship('tblDetails', backref='dmemory', lazy=True)
    price = db.Column(db.Numeric(10,2), nullable=True, default=0.00)

class tblGraphic(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    graphic = db.Column(db.String(20), nullable=True, default='')
    dgraphic = db.relationship('tblDetails', backref='dgraphic', lazy=True)
    price = db.Column(db.Numeric(10,2), nullable=True, default=0.00)

class tblDisplay(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    display = db.Column(db.String(20), nullable=True, default='')
    ddisplay = db.relationship('tblDetails', backref='ddisplay', lazy=True)
    price = db.Column(db.Numeric(10,2), nullable=True, default=0.00)

class tblStorage(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    storage = db.Column(db.String(20), nullable=True, default='')
    dstorage = db.relationship('tblDetails', backref='dstorage', lazy=True)
    price = db.Column(db.Numeric(10,2), nullable=True, default=0.00)

class tblBattery(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    battery = db.Column(db.String(50), nullable=True, default='')
    dbattery = db.relationship('tblDetails', backref='dbattery', lazy=True)
    price = db.Column(db.Numeric(10,2), nullable=True, default=0.00)

class tblCamera(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    camera = db.Column(db.String(50), nullable=True, default='')
    dcamera = db.relationship('tblDetails', backref='dcamera', lazy=True)
    price = db.Column(db.Numeric(10,2), nullable=True, default=0.00)

class tblAudio(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    audio = db.Column(db.String(50), nullable=True, default='')
    daudio = db.relationship('tblDetails', backref='daudio', lazy=True)
    price = db.Column(db.Numeric(10,2), nullable=True, default=0.00)

class tblDetails(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(20), nullable=True, default='')
    price = db.Column(db.Numeric(10,2), nullable=True, default=0.00)
    height = db.Column(db.String(20), nullable=True, default='')
    width = db.Column(db.String(20), nullable=True, default='')
    depth = db.Column(db.String(20), nullable=True, default='')
    weight = db.Column(db.String(20), nullable=True, default='')
    brand = db.Column(db.String(36), db.ForeignKey('tbl_brand.id'), nullable=False)
    processor = db.Column(db.String(36), db.ForeignKey('tbl_processor.id'), nullable=False)
    memory = db.Column(db.String(36), db.ForeignKey('tbl_memory.id'), nullable=False)
    graphic = db.Column(db.String(36), db.ForeignKey('tbl_graphic.id'), nullable=False)
    display = db.Column(db.String(36), db.ForeignKey('tbl_display.id'), nullable=False)
    storage = db.Column(db.String(36), db.ForeignKey('tbl_storage.id'), nullable=False)
    battery = db.Column(db.String(36), db.ForeignKey('tbl_battery.id'), nullable=False)
    camera = db.Column(db.String(36), db.ForeignKey('tbl_camera.id'), nullable=False)
    audio = db.Column(db.String(36), db.ForeignKey('tbl_audio.id'), nullable=False)
    product = db.Column(db.String(36), db.ForeignKey('tbl_product.id'), nullable=False)
    note = db.Column(db.Text(), nullable=True, default='')

class tblProduct(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    model = db.Column(db.String(20), nullable=True, default='')
    colors = db.relationship('tblColor', backref='colors', lazy=True)
    photo = db.Column(db.String(255), nullable=False, default='no-photo.png')
    createdOn = db.Column(db.DateTime, default=datetime.utcnow)
    createdBy = db.Column(db.String(36), db.ForeignKey('tbl_user.id'), nullable=False)
    details = db.relationship('tblDetails', backref='details', lazy=True)


#Define class schema
class UserSchema(ma.ModelSchema):
    class Meta:
        model = tblUser

class PostSchema(ma.ModelSchema):
    class Meta:
        model = tblPost

    likedBy = fields.Nested(UserSchema, many=True, only=['id', 'username'])

class BrandSchema(ma.ModelSchema):
    class Meta:
        model = tblBrand


#Custome function
def del_ex_file(ex_file, dir_file):
    if ex_file != 'default.png':
        ex_file = dir_file + '/static/uploads/' + ex_file
        try:
            os.remove(ex_file)
        except:
            return 'No file found'


#Get route from route.py
from app import route
import os
from app import db, app, safe, mail, bcrypt, upload, login_manager, del_ex_file, basedir
from app import tblPost, tblUser, tblProfile
from app import RegisterForm, LoginForm, ProfileDetailsForm
from app import Message, SignatureExpired, SQLAlchemyError
from flask import request, redirect, render_template, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from uuid import uuid4


@login_manager.user_loader
def load_user(id):
    return tblUser.query.get(id)


@app.route('/error')
def error():
    return render_template('views/error.html')


@app.route('/')
@login_required
def index():
    if current_user.isConfirm != True:
        flash('Please confirm your email address to fully access Stripe!', 'danger')
    return render_template('views/index.html')


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            firstname = request.form['firstname']
            lastname = request.form['lastname']
            username = request.form['username']
            gender = request.form['gender']
            birthdate = form.birthdate.data
            email = request.form['email']
            password = request.form['password']

            #Generate unique Id
            id = str(uuid4())

            #Encrypt the password field
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

            #User to register
            requestedUser = tblUser(id= id, firstname= firstname, lastname= lastname, username= username, gender= gender, birthdate= birthdate, email= email, password= hashed_password)

            try:
                db.session.add(requestedUser)
                db.session.commit()
                user = tblUser.query.filter_by(username= username).first()
                login_user(user)
                
                return redirect('/verify')
            except SQLAlchemyError as error:
                print(str(error))
                db.session.rollback()
                return 'Register failed'
    return render_template('views/register.html', form= form)


@app.route('/login', methods=['POST', 'GET'])
def login():
    logout_user()
    form = LoginForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            username = request.form['username']
            password = request.form['password']
            user = tblUser.query.filter_by(username= username).first()
            while user is not None:
                isMatch = bcrypt.check_password_hash(user.password, password)
                if isMatch is True:
                    login_user(user)
                    return redirect('/')
                return 'Password is incorrect'
            return 'Username does not exist'
    return render_template('views/login.html', form = form)


@app.route('/logout', methods=['POST'])
def logout():
    logout_user()
    return redirect('/login')


@app.route('/verify', methods=['POST', 'GET'])
def verify():
    message = 'Please verify your email address'
    if request.method == 'POST':
        if request.form['email']:
            email = request.form['email']
        else:
            email = current_user.email
        #Generate token and mail confirmation
        token = safe.dumps(email, salt='confirm-email')
        msg = Message('Email Verification', recipients=[email])
        confirm_link = url_for('check', token= token, _external=True)
        msg.body = f'Hi {current_user.firstname}! Please click here to verify your email address ' + confirm_link
        try:
            mail.send(msg)
            message = f"<div class='feedback-msg'><h1>Please verify your email</h1><br><br><p>Hi {current_user.username}! We have sent you a confirmation to this email:</p><p><b>{email}</b></p><br><p>Click the confirmation link to begin using <b>Stripe</b></p><br><p>Did not recieve an email? Check the spam folder, It may have been caught by a filter. If you still did not recieve, you can <a href='/verify'>resend the confirmation email</a></div>"

            return render_template('views/feedback.html', message= message)
        except: 
            return 'Email has not been sent'

    return render_template('views/verify.html', message= message)


@app.route('/check/<token>')
def check(token):
    try:
        email = safe.loads(token, salt='confirm-email', max_age=360)
        user = tblUser.query.filter_by(email= email).first()
        if user:
            user.isConfirm = True
            try: 
                db.session.commit()
                message = f"<div class = 'feedback-msg'><h1>Thanks for your confirmation!</h1></div>"
                return render_template('views/feedback.html', message= message)
            except SQLAlchemyError as error:
                print(str(error))
                return 'Unable to make change'
        else:
            return 'Email does not match'
    except SignatureExpired:
        return 'Token Expired! Please try again!'
    return 'Email verified! Thanks you very much...'


@app.route('/profile/<id>')
def profile(id):
    user = tblUser.query.get(id)
    return render_template('views/profile.html', user = user)


@app.route('/profile/details/<id>', methods=['POST', 'GET'])
def profile_details(id):
    form = ProfileDetailsForm()
    #Get user profile
    user = tblUser.query.get(id)
    profile = None
    if user.profile:
        profile = user.profile
    if request.method == 'POST':
        if form.validate_on_submit():
            #Request form data
            status = request.form['status']
            phone = request.form['phone']
            company = request.form['company']
            hometown = request.form['hometown']
            location = request.form['location']
            bio = request.form['bio']
            if user.profile:
                user.profile[0].status = status
                user.profile[0].phone = phone
                user.profile[0].company = company
                user.profile[0].hometown = hometown
                user.profile[0].location = location
                user.profile[0].bio = bio   
                try:
                    db.session.commit()
                    return redirect(f'/profile/{id}')
                except:
                    return redirect(f'/profile/details/{id}')

            profile_id = str(uuid4())
            profile = tblProfile(id= profile_id, status= status, phone= phone, company= company, hometown= hometown, location= location, bio= bio, user= id)
            try:
                db.session.add(profile)
                db.session.commit()
                return redirect(f'/profile/{id}')
            except:
                flash()
                return redirect(f'/profile/details/{id}')

    return render_template('views/edit_profile.html', form= form, profile= profile)


@app.route('/profile/photo/<id>', methods=['POST'])
def profile_photo(id):
    photo = request.files['file']
    filename = photo.filename
    if filename != '':
        user = tblUser.query.get(id)
        if user.profile:
            if user.profile[0].photo != 'default.png':
                del_ex_file(user.profile[0].photo, basedir)
            extension = filename.split('.')[1]
            filename = str(uuid4()) + '.' + extension
            user.profile[0].photo = filename
            photo.filename = filename
            upload_file = upload.save(photo)
            try:
                db.session.commit()
                return jsonify({'path': filename})
            except:
                return redirect('/error')
        else:
            extension = filename.split('.')[1]
            filename = str(uuid4()) + '.' + extension  
            photo.filename = filename 
            profile_id = str(uuid4())
            profile = tblProfile(id= profile_id, photo= filename, user= id)
            try:
                db.session.add(profile)
                db.session.commit()
                upload_file = upload.save(photo)
                return jsonify({'path': filename})
            except:
                return redirect('/error')
    return jsonify({'path': '/static/uploads/default.png'})



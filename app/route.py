import os, json, sqlite3
from app import db, app, safe, mail, bcrypt, upload, login_manager, del_ex_file, basedir
from app import tblPost, tblUser, tblProfile, tblProduct, tblColor, tblCamera, tblDetails, tblDisplay, tblGraphic, tblMemory, tblProcessor, tblStorage, tblAudio, tblBattery, tblBrand
from app import PostSchema, UserSchema, BrandSchema
from app import RegisterForm, LoginForm, ProfileDetailsForm, PostForm
from app import Message, SignatureExpired, SQLAlchemyError
from flask import request, redirect, render_template, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from uuid import uuid4
from collections import namedtuple


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
        flash('Please confirm your email address to fully access Geeze!', 'danger')
    posts = tblPost.query.all()
    return render_template('views/index.html', posts= posts)


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
            profile_id = str(uuid4())

            #Encrypt the password field
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

            #User to register
            requestedUser = tblUser(id= id, firstname= firstname, lastname= lastname, username= username, gender= gender, birthdate= birthdate, email= email, password= hashed_password)
            userProfile = tblProfile(id= profile_id, user= id)
            try:
                db.session.add(requestedUser)
                db.session.add(userProfile)
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


@app.route('/post/add', methods=['POST', 'GET'])
@login_required
def post_add():
    form = PostForm()
    if request.method == 'POST':
        title = request.form['title']
        photo = request.files['photo']
        id = str(uuid4())
        if photo.filename != '':
            extension = photo.filename.split('.')[1]
            filename = str(uuid4()) + '.' + extension
            photo.filename = filename
            post_photo = upload.save(photo)
        else:
            filename = 'default.png'
        
        Post = tblPost(id= id, title= title, photo= filename, createdBy= current_user.id)
        try:
            db.session.add(Post)
            db.session.commit()
            return redirect('/')
        except:
            return 'Unable to post the product'
    return render_template('views/add_post.html', form= form)


@app.route('/post/photo', methods=['POST'])
def post_photo():
    photo = request.files['file']
    temp_photo = upload.save(photo)
    return jsonify({'path': photo.filename})


@app.route('/post/like/<id>', methods=['POST'])
def post_like(id):
    post = tblPost.query.get(id)
    isLiked = False
    for user in post.likedBy:
        if user.id == current_user.id:
            isLiked = True
    try:
        if isLiked is True:
            post.likedBy.remove(current_user)
        else:
            post.likedBy.append(current_user)
        db.session.commit()
        get_post = tblPost.query.get(id)
        post_json = PostSchema()
        get_liked = post_json.dump(get_post)
        return jsonify({'id': id, 'isLike': isLiked, 'liked': get_liked})
    except:
        return 'Failed'


@app.route('/post/edit/<id>', methods=['POST', 'GET'])
def post_edit(id):
    form = PostForm()
    post = tblPost.query.get_or_404(id)
    if request.method == 'POST':
        title = request.form['title']
        post.title = title
        try: 
            db.session.commit()
            return redirect('/')
        except:
            return 'Unable to update the post'
    return render_template('views/edit_post.html', form= form, post= post)
    

@app.route('/post/delete/<id>', methods=['POST'])
def post_delete(id):
    post = tblPost.query.get_or_404(id)
    if post.photo != 'default.png':
        del_ex_file(post.photo, basedir)
    try:
        db.session.delete(post)
        db.session.commit()
        return redirect('/')
    except:
         return 'Error have occured while deleting this post!'


@app.route('/products')
@login_required
def products():
    products = tblProduct.query.all()
    colors = tblColor.query.all()
    processors = tblProcessor.query.all()
    memories = tblMemory.query.all()
    graphics = tblGraphic.query.all()
    displays = tblDisplay.query.all()
    storages = tblStorage.query.all()
    batteries = tblBattery.query.all()
    cameras = tblCamera.query.all()
    audios = tblAudio.query.all()
    brands = tblBrand.query.all()
    return render_template('views/product.html', products= products, colors= colors, processors= processors, memories= memories, graphics= graphics, displays= displays, storages= storages, batteries= batteries, cameras= cameras, audios= audios, brands= brands)


@app.route('/product/details/add', methods=['POST'])
def product_add():
    con = sqlite3.connect('app/database.db')
    idAttr = request.form['inpId']
    idName = idAttr.split('inp')[1]
    name = idName.lower()
    value = request.form['value']
    id = str(uuid4())
    try:
        curser = con.cursor()
        curser.execute('INSERT INTO tbl_{} VALUES(?, ?, ?)'.format(name), (id, value, 0.00))
        con.commit()
        curser.execute('SELECT * FROM tbl_{}'.format(name))
        options = curser.fetchall()

        return jsonify({'options': options, 'id': name})
    except:
        return 'Failed'


@app.route('/product/brand/add', methods=['POST'])
def brand_add():
    brand = request.form['input']
    id = str(uuid4())
    Brand = tblBrand(id= id, brand= brand, createdBy= current_user.id)
    try: 
        db.session.add(Brand)
        db.session.commit()
        data = tblBrand.query.all()
        json = BrandSchema(many=True)
        brands = json.dump(data)
        return jsonify({'brands': brands})
    except:
        return 'Failed'


@app.route('/product/photo', methods=['POST'])
def product_photo():
    photo = request.files['file']
    temp_photo = upload.save(photo)
    return jsonify({'path': photo.filename})


@app.route('/product/add', methods=['POST'])
def products_add():
    jsons = request.form['items']
    lists = json.loads(jsons, object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))

    if len(request.files) > 0:
        photo = request.files['file']
        extension = photo.filename.split('.')[1]
        filename = str(uuid4()) + '.' + extension
        del_ex_file(photo.filename, basedir)
        photo.filename = filename
        post_photo = upload.save(photo)
    else:
        filename = 'no-photo.png'
    
    if lists[0].model != lists[0].newModel:
        product = tblProduct.query.get(lists[0].model)
        if filename != 'no-photo.png':
            product.photo = filename
        try:
            for item in lists:
                did = str(uuid4())
                details = tblDetails(id= did, name= item.name, price= item.price, brand= item.brand, processor= item.processor, memory= item.memory, graphic= item.graphic, display= item.display, storage= item.storage, battery= item.battery, camera= item.camera, audio= item.audio, product= lists[0].model, note= item.details)
                product.details.append(details)
                db.session.commit()
            return jsonify({'feedback': 'Added!'})
        except:
            return jsonify({'feedback': 'Failed'})

    else:
        pid = str(uuid4())
        product = tblProduct(id= pid, model= lists[0].model, photo= filename, createdBy= current_user.id)
        
        try:
            db.session.add(product)
            db.session.commit()
            gproduct = tblProduct.query.get(pid)
            for color in lists[0].colors:
                cid = str(uuid4())
                pcolor = tblColor(id= cid, color= color.name, hex= color.hex, product= pid)
                try:
                    db.session.add(pcolor)
                    db.session.commit()
                except:
                    return 'Failed'
            for item in lists:
                did = str(uuid4())
                details = tblDetails(id= did, name= item.name, price= item.price, brand= item.brand, processor= item.processor, memory= item.memory, graphic= item.graphic, display= item.display, storage= item.storage, battery= item.battery, camera= item.camera, audio= item.audio, product= pid, note= item.details)
                db.session.add(details)
                db.session.commit()
            return jsonify({'feedback': 'Added!'})
        except:
            return jsonify({'feedback': 'Failed'})


@app.route('/product/<id>')
def product(id):
    product = tblDetails.query.get(id)
    return render_template('views/product_details.html', product= product)

@app.route('/product/edit/<id>', methods=['POST', 'GET'])
def product_edit(id):
    product = tblProduct.query.get(id)
    return render_template('views/edit_product.html', product= product)



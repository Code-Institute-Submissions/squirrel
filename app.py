import os
from os import path
if path.exists("env.py"):
    import env
from flask import Flask, render_template, url_for, flash, redirect, request, jsonify
from forms import RegistrationForm, LoginForm, EntryForm, NewEntryForm
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from is_safe_url import is_safe_url
import socket
from datetime import datetime
import cloudinary
import cloudinary.uploader
import cloudinary.api
import math

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['MONGO_DBNAME'] = os.environ.get('MONGO_DBNAME')
app.config['MONGO_URI'] = os.environ.get('MONGO_URI')
app.config['CLOUDINARY_URL'] = os.environ.get('CLOUDINARY_URL')


mongo = PyMongo(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

login_manager.init_app(app)



"""
USER MANAGEMENT
"""

class User(UserMixin):
    def __init__(self, user):
        self.user = user
        self.username = user['username']
        self.id = user['_id']

    def get_id(self):
        object_id = self.user['_id']
        return str(object_id)



@login_manager.user_loader
def load_user(user_id):
    user =  mongo.db.users.find_one({'_id' : ObjectId(user_id)})
    return User(user)


"""
# Login Route
# ===========
#
# The following manages the login route.
# If a session already exists, the user is redirected to the listing page.
#
# If not, the login page is displayed.
# Several requirements exist for the user to login upon submission of the form:
# 1) The account has to exist in the database
# 2) The submitted password has to match the hashed password saved in the database
#
# The 'next' argument is sent through the url if a user tried to access a page behind a login wall.
# This argument is used to redirect the user to the appropriate page,
# after having verified that it is a safe url.
"""

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect to listing page if user is logged in
    if current_user.is_authenticated:
        return redirect(url_for('listing'))
    form = LoginForm()
    users = mongo.db.users
    if form.validate_on_submit():
        user = users.find_one({'email' : form.email.data})
        # If user exists and password matches password in db, log in and create a user session
        if user and bcrypt.check_password_hash(user['password'], form.password.data.encode('utf-8')):
            username = user['username']
            # Save session, even after browser is closed
            login_user(User(user), remember = form.remember.data)

            # Checks where to redirect the user after login
            next_page = request.args.get('next')
            flash(f'Welcome to squirrel, {username}.', 'success')

            # If unauthorized page has been accessed before being logged in,
            # redirect to it after login if it is safe
            if next_page and is_safe_url(next_page, socket.gethostname()):
                return redirect(next_page)

            # If not, redirect to the listing page
            else:
                return redirect(url_for('listing'))
        else:
            flash('Login unsucessful, please check email and password.', 'danger')

    return render_template('pages/login.html', title="Login", form=form)


"""
# Registration Route
# ==================
#
# The following manages new user registration.
# Upon form submission, if the email does not already exist as an account in the database,
# and the two password fields match, a new user is inserted.
# The password is hashed with bcrypt for added security.
#
# Once the account is created, the user is automatically logged in with this new account
# and redirected to the listing page.
"""

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('listing'))
    form = RegistrationForm()
    users = mongo.db.users
    if form.validate_on_submit():
        existing_email = users.find_one({'email': form.email.data})
        # Create new user only if email is not already in use
        if existing_email is None:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            users.insert_one({
                "username": form.username.data,
                "email": form.email.data,
                "password": hashed_password,
            })
            # Log in once user is created in db
            user = users.find_one({'email': form.email.data})
            login_user(User(user), remember = False)
            flash(f'Account created for {form.username.data}.', 'success')
            return redirect(url_for('listing'))
        else:
            flash(f'Something went wrong with the information provided.', 'danger')

    return render_template('pages/registration.html', title="Registration", form=form)

"""
# Logout Route
# ============
#
# The following redirects the user to the login page and deletes the session cookie.
"""

@app.route('/logout')
def logout():
    logout_user()
    flash(f'Sucessfully logged out.', 'success')
    return redirect(url_for('login'))


"""
# Listing Route
# =============
#
# The following displays a listing of user reviews.
# The query to the database will be different if a tag has been passed to the url.
#
# Several variables are created to manage pagination:
# limit: defines the number of reviews to display on the page
# page: defines which page to be viewed, this is sent as an argument through the url
# offset: defines how many elements to skip in the database query
# max_page: defines the maximum number of pages
#
# If a non existant page is sent as an argument through the url, user is redirected to a 404 page.
#
# In the query to mongodb, a field called 'sort_date' is added to each result.
# It takes the value of 'updated_on' if existant, if not it takes the value of 'created_on'.
# This allows to sort the entries by their latest update or creation date.
"""

@app.route('/listing')
@app.route('/listing/<tag>')
@login_required
def listing(tag = None):

    # Change search query if tag exists or not
    if tag:
        match_query = {'user_id' : current_user.id, 'tags': tag}
    else:
        match_query = {'user_id' : current_user.id}

    # Number of entries per page
    limit = 12

    if 'page' in request.args and request.args['page'].isnumeric():
        # Define which page to view based on get request
        page = int(request.args['page']) 
    else:
        # if no pages are defined, view page 1
        page = 1

    # Set index of first result of query
    offset = (page - 1) * limit

    # Count number of results for the query
    entry_count = mongo.db.entries.count_documents(match_query)
    max_page = math.ceil(entry_count/limit)
    
    # Ensure that if an inexistant page is entered in the address bar, a 404 page is returned
    if entry_count !=0 and page > max_page or page <= 0:
        return render_template('pages/404.html',  title="Page Not Found")

    # Query that returns entries, sorted by creation date or update date
    entries = mongo.db.entries.aggregate([
        {'$match': match_query},
        {'$addFields': {
            # Sorts by created date, or updated date if it exists
            'sort_date': {
                '$cond': {
                    'if': '$updated_on', 'then': '$updated_on', 'else': '$created_on'
                }
            }              
        }},
        {'$sort': {'sort_date': -1}},
        {'$skip': offset},
        {'$limit': limit}
    ])

    # Create next and previous urls for pagination
    current_url = request.path
    next_url = current_url + "?page=" + str(page + 1) if (page + 1) <= max_page else None
    prev_url = current_url + "?page=" + str(page - 1) if (page - 1) > 0 else None

    return render_template('pages/listing.html', title="Listing", entries=entries, tag=tag, next_url = next_url, prev_url = prev_url, entry_count = entry_count)


"""
# Entry Route
# ===========
# This route displays reviews generated by the user.
# If the entry was created by logged in user, it pulls its information from the database
# using its id.
#
# The input fields in the html are populated by this information from the database.
#
# If a user tries to access an entry created by another user (through the url),
# they are redirected to a 403 page.

"""

@app.route('/entry/<entry_id>')
@login_required
def entry(entry_id):
    form = EntryForm()
    the_entry = mongo.db.entries.find_one({"_id": ObjectId(entry_id)})
    if the_entry["user_id"] == current_user.id:
        form.name.data = the_entry["name"]
        form.description.data = the_entry["description"]
        form.rating.data = str(the_entry["rating"])
        form.hidden_id.data = entry_id
        if the_entry.get("tags") is not None:
            form.hidden_tags.data = ','.join(the_entry["tags"])
        return render_template('pages/entry.html',  title="Entry" , entry=the_entry, form = form)
    else:
        return render_template('pages/403.html',  title="Forbidden")


@app.route('/update_fav/<entry_id>', methods=['POST', 'GET'])
@login_required
def update_fav(entry_id):
    form = EntryForm()
    entries = mongo.db.entries
    timestamp = datetime.now()
    the_entry = entries.find_one({"_id": ObjectId(entry_id)})
    if the_entry["user_id"] == current_user.id:
        entries.update_one(
            {"_id": ObjectId(entry_id)},
            { "$set":
                {
                    "is_fav": form.is_fav.data,
                    "updated_on": timestamp
                }
            },
        )
        return jsonify( {"updated_on" : timestamp.strftime("%d/%m/%Y at %H:%M:%S"),
                        "success_message": "Review sucessfully updated.",
                        "message_class": "alert-success"})
    else:
        return render_template('pages/403.html',  title="Forbidden")


@app.route('/update_name/<entry_id>', methods=['POST', 'GET'])
@login_required
def update_name(entry_id):
    form = EntryForm()
    entries = mongo.db.entries
    timestamp = datetime.now()
    new_name = form.name.data
    the_entry = entries.find_one({"_id": ObjectId(entry_id)})
    if the_entry["user_id"] == current_user.id:
        if len(new_name) > 0 and len(new_name) <= 30:
            entries.update_one(
                {"_id": ObjectId(entry_id)},
                { "$set":
                    {
                        "name": new_name,
                        "updated_on": timestamp
                    }
                },
            )
            return jsonify( {"updated_on" : timestamp.strftime("%d/%m/%Y at %H:%M:%S"),
                            "success_message": "Name sucessfully updated.",
                            "message_class": "valid-update"})
    else:
        return render_template('pages/403.html',  title="Forbidden")


@app.route('/update_description/<entry_id>', methods=['POST', 'GET'])
@login_required
def update_description(entry_id):
    form = EntryForm()
    entries = mongo.db.entries
    timestamp = datetime.now()
    new_description = form.description.data
    the_entry = entries.find_one({"_id": ObjectId(entry_id)})
    if the_entry["user_id"] == current_user.id:
        if len(new_description) > 0 and len(new_description) <= 2000:
            entries.update_one(
                {"_id": ObjectId(entry_id)},
                { "$set":
                    {
                        "description": form.description.data,
                        "updated_on": timestamp
                    }
                },
            )
            return jsonify( {"updated_on" : timestamp.strftime("%d/%m/%Y at %H:%M:%S"),
                            "success_message": "Description sucessfully updated.",
                            "message_class": "valid-update"})
    else:
        return render_template('pages/403.html',  title="Forbidden")


@app.route('/update_rating/<entry_id>', methods=['POST', 'GET'])
@login_required
def update_rating(entry_id):
    form = EntryForm()
    entries = mongo.db.entries
    timestamp = datetime.now()
    the_entry = entries.find_one({"_id": ObjectId(entry_id)})
    if the_entry["user_id"] == current_user.id:
        entries.update_one(
            {"_id": ObjectId(entry_id)},
            { "$set":
                {
                    "rating": int(form.rating.data),
                    "updated_on": timestamp
                }
            },
        )
        return jsonify( {"updated_on" : timestamp.strftime("%d/%m/%Y at %H:%M:%S"),
                        "success_message": "Rating sucessfully updated.",
                        "message_class": "valid-update"})
    else:
        return render_template('pages/403.html',  title="Forbidden")



@app.route('/update_tags/<entry_id>', methods=['POST', 'GET'])
@login_required
def update_tags(entry_id):
    form = EntryForm()
    entries = mongo.db.entries
    timestamp = datetime.now()
    the_entry = entries.find_one({"_id": ObjectId(entry_id)})
    if the_entry["user_id"] == current_user.id:
        if len(form.tags.data) == 0:
            entries.update_one(
                {"_id": ObjectId(entry_id)},
                { "$unset":
                    {
                        "tags": "",
                        "updated_on": timestamp
                    }
                },
            )
            return jsonify( {"updated_on" : timestamp.strftime("%d/%m/%Y at %H:%M:%S"),
                            "success_message": "Tags sucessfully updated.",
                            "message_class": "valid-update"})
            
        else:
            # turn tags to a lowercase list and remove duplicates
            lowercase_tags = form.tags.data.lower().split(',')

            final_tags = []
            for x in lowercase_tags:
                if x not in final_tags:
                    final_tags.append(x)

            entries.update_one(
                {"_id": ObjectId(entry_id)},
                { "$set":
                    {
                        "tags": final_tags,
                        "updated_on": timestamp
                    }
                },
            )
            return jsonify( {"updated_on" : timestamp.strftime("%d/%m/%Y at %H:%M:%S"),
                            "success_message": "Tags sucessfully updated.",
                            "message_class": "valid-update"})
    else:
        return render_template('pages/403.html',  title="Forbidden")


@app.route('/update_image/<entry_id>', methods=['POST', 'GET'])
@login_required
def update_image(entry_id):
    form = EntryForm()
    entries = mongo.db.entries
    timestamp = datetime.now()
    image = request.files[form.image.name]
    uploaded_image = cloudinary.uploader.upload(image, width = 800, quality = 'auto')
    image_url = uploaded_image.get('secure_url')
    the_entry = entries.find_one({"_id": ObjectId(entry_id)})
    if the_entry["user_id"] == current_user.id:
        entries.update_one(
            {"_id": ObjectId(entry_id)},
            { "$set":
                {
                    "image": image_url,
                    "updated_on": timestamp
                }
            },
        )
        return jsonify({"new_image" : image_url,
                        "updated_on" : timestamp.strftime("%d/%m/%Y at %H:%M:%S"),
                        "success_message": "Image sucessfully updated.",
                        "message_class": "valid-update"})
    else:
        return render_template('pages/403.html',  title="Forbidden")

"""
# Add Route:
# ==========
#
# This route allows users to add a new entry to the database.
# Upon validation, every field is checked and inserted into mongodb as a new
# document.
"""
@app.route('/add', methods=['GET', 'POST'])
@login_required
def new_entry():
    form = NewEntryForm()
    entries = mongo.db.entries
    if form.validate_on_submit():
        # Images are uploaded to cloudinary, and their url is inserted into the image
        # field of the database.
        if form.image.data:
            image = request.files[form.image.name]
            uploaded_image = cloudinary.uploader.upload(image, width = 800, quality = 'auto')
            image_url = uploaded_image.get('secure_url')

        else:
            # A default placeholder image is selected if no image has been inputed.
            image_url = '/static/img/image-placeholder.png'
        

        # The tags are retrieved as a string of words separated by commas.
        # We generate a list by splitting the string, words are lowercased
        # and we ensure no tags are duplicated.
        if form.hidden_tags.data != "":
            lowercase_tags = form.hidden_tags.data.lower().split(',')
            tags = []
            for tag in lowercase_tags:
                if tag not in tags:
                    tags.append(tag)

        else:
            tags = None

        # The data from the form creates a new document in the database.
        new_entry_id = entries.insert_one({
            "name": form.name.data,
            "user_id": current_user.id,
            "description": form.description.data,
            "rating": int(form.rating.data),
            "is_fav": form.is_fav.data,
            "image" : image_url,
            "tags": tags,
            "created_on": datetime.now()
        })

        flash(f'Review for “{form.name.data}” created successfully.', 'success')
        return redirect(url_for('entry', entry_id = new_entry_id.inserted_id))
    return render_template('pages/new_entry.html',  title="New Entry", form=form)


@app.route('/delete/<entry_id>')
@login_required
def delete(entry_id):
    the_entry = mongo.db.entries.find_one({"_id": ObjectId(entry_id)})
    if the_entry["user_id"] == current_user.id:
        review_name = the_entry["name"]
        mongo.db.entries.delete_one({"_id": ObjectId(entry_id)})
        flash(f'Review for “{review_name}” was deleted.', 'success')
        return redirect(url_for('listing'))
    else:
        return render_template('pages/403.html',  title="Forbidden")


@app.route('/search/', methods=["POST"])
@login_required
def get_search():
    return redirect(url_for("search", search_term=request.form.get("search_field")))


# Generate page with search results
@app.route('/search/<search_term>', methods=["POST", "GET"])
@login_required
def search(search_term):
    entries = mongo.db.entries
    entries.create_index([
        ("name", "text"),
        ("description", "text"),
        ("tags", "text"),
    ])

    result = entries.find({'user_id' : current_user.id, "$text": {"$search": search_term}}, 
    {'score': {'$meta': 'textScore'}}).sort([('score', {'$meta': 'textScore'})])

    # Count the number of results of the query
    num_entries = len(list(result.clone()))

    return render_template('pages/search.html',  title="Results for " + search_term, num_entries=num_entries, entries=result, search_term=search_term)


@app.errorhandler(404) 
def invalid_route(e): 
    return render_template('pages/404.html',  title="Page Not Found")


if __name__ == '__main__':
    app.run(host=os.environ.get('HOSTNAME'),
            port=int(os.environ.get('PORT')),
            debug=os.environ.get('DEV'))

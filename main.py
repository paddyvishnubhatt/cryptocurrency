import logging
from flask import Flask, Response, session, render_template, request, url_for, redirect, abort
import json
import urllib
from markupsafe import Markup
import time
from flask import send_from_directory
import os
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
import base64

import utils.utils as utils
import exchange.exchange as exchange
import portfolio.portfolio as portfolio

PROJECT_REMINDER_TITLE = "CC Reminder: Your CC Balance needs to checked"
ADMIN_WELCOME_TITLE = "CC Admin User Created"
ADMIN_WELCOME_MESSAGE = "Admin user for {username } created. Please go ahead and create and add/invite users to the exchange"
USER_WELCOME_TITLE="Welcome to CC"
USER_WELCOME_MESSAGE="Hello {userId}\nA user has been created for you in the exchange. " + \
                        "Please login at your earliest and review your balance and check out the markets, Thank you."

app = Flask(__name__)
app.secret_key = "super_secret_key"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.header_loader
def load_user_from_header(header_val):
    header_val = header_val.replace('Basic ', '', 1)
    try:
        header_val = base64.b64decode(header_val)
        authstr = header_val.split(":")
        userId = authstr[0]
        user = utils.get_user_from_db(userId)
        if user and authstr[1] == user.password:
            return user
        elif user is None and userId == "superuser" and authstr[1] == "password":
            user = utils.update_user('superuser', 'superuser@lafoot.com', 'Superuser', 'password', None)
            time.sleep(1)
            return user
    except TypeError:
        pass
    return None

# callback to reload the user object
@login_manager.user_loader
def load_user(userid):
    return utils.get_user_from_db(userid)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = utils.get_user_from_db(username)
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('landing_page'))
        else:
            return abort(401)
    else:
        return render_template('login.html')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('landing_page'))

# handle login failed
@app.errorhandler(401)
def page_not_found(e):
    return render_template(
        "entry_error.html",
        h1Message="Authentication Error, Go back and re-enter",
        title="Invalid User Error",
        message="Please go back and use another identity and retry. If you do not have an account, please request the Administrator")

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def root():
    return render_template('root.html')

@app.route('/request_for_admin')
def request_for_admin():
    return render_template('admin_request.html')

@app.route('/api/v1/check_for_user/<userId>')
def check_for_user(userId):
    user = utils.get_user_from_db(userId)
    if user:
        return json.dumps(True)
    else:
        return json.dumps(False)

@app.route('/api/v1/about_page')
def about_page():
    return render_template('about.html')

@app.route('/api/v1/admin_page')
@login_required
def admin_page():
    cu = current_user.identity
    return render_template(
        'admin.html',
        current_user=cu)

@app.route('/api/v1/landing_page')
@login_required
def landing_page():
    user = current_user
    print user.identity + ", " + user.type
    if user.type == "Admin":
        return admin_page()
    elif user.type == "Superuser":
        return admin_page()
    else:
        return portfolio.show_portfolio(user.identity)

@app.route('/api/v1/show_users')
@login_required
def show_users():
    users = utils.get_users_from_db()
    cu = current_user.identity
    return render_template(
        'users.html',
        current_user=cu,
        users= users)

@app.route('/api/v1/show_markets')
@login_required
def show_markets():
    return exchange.show_markets()

@app.route('/api/v1/submitted_admin_user', methods=['POST'])
def submitted_admin_user():
    username = request.form.get('username')
    user = utils.get_user_from_db(username)
    if user:
        return render_template(
            "entry_error.html",
            h1Message="User ID Error, Go back and re-enter",
            title="User Add Error",
            message=username + " already is an existing user, Please go back and use another identity and submit")
    else:
        email = request.form.get('email')
        password = request.form.get('password')
        user = utils.update_user(username, email, "Admin", password)
        try:
            utils.send_message(user, ADMIN_WELCOME_TITLE, ADMIN_WELCOME_MESSAGE.format(username=username))
        except RuntimeError as e:
            print e
        return render_template('root.html')

@app.route('/api/v1/show_user/<identity>')
@login_required
def show_user(identity):
    user = utils.get_user_from_db(identity)
    if user is not None and identity == "__CREATE__":
        # edit current/existing user
        cu = current_user.identity
        return render_template(
            'user.html',
            current_user = cu,
            user=user)
    else:
        # create new user
        cu = current_user.identity
        return render_template(
            'user.html',
             current_user=cu)

@app.route('/api/v1/set_user/<userId>', methods=['PATCH'])
@login_required
def set_user(userId):
    user = utils.get_user_from_db(userId)
    email = request.form.get('email')
    password  = request.form.get('password')
    if user:
        isChanged = False
        if user.email != email:
            user.email = email
            isChanged = True
        if user.password != password:
            user.password = password
            isChanged = True
        if isChanged == True:
            user.put()


@app.route('/api/v1/submitted_user', methods=['POST', 'GET'])
@login_required
def submitted_user():
    if request.method == 'GET':
        return redirect(url_for('landing_page'))
    userId = request.form.get('identity')
    if userId == "superuser":
        return render_template(
            "entry_error.html",
            h1Message="User ID Error, Go back and re-enter",
            title="User Add Error",
            message=userId + " is a system user, Please go back and use another identity and submit")
    email = request.form.get('email')
    type = request.form.get('type')
    password = request.form.get('password')
    print "user: " + str(userId) + ", " + str(email) + ", " + str(type) + ", " + str(password)
    user = utils.update_user(userId, email, type, password)
    try:
        utils.send_message(user, USER_WELCOME_TITLE,
           USER_WELCOME_MESSAGE.format(userId=user.identity))
    except RuntimeError:
        pass
    return landing_page()

@app.route('/api/v1/send_email', methods=['POST'])
def send_email():
    content =  request.form.get('content')
    tolist = request.form.getlist('tolist[]')
    title = PROJECT_REMINDER_TITLE
    utils.send_reminders(tolist, title, content)
    return "OK", 200

@app.route('/api/v1/manage', methods=['GET', 'POST'])
def manage():
    utils.run_manage()
    return "OK", 200

@app.route('/api/v1/update_token', methods=['POST'])
def update_token():
    if current_user and current_user.is_anonymous == False:
        username = current_user.identity
        token = request.form.get('token')
        utils.update_token(username, token)
    return "OK", 200


@app.route('/api/v1/delete_user/<userId>', methods=['DELETE'])
@login_required
def delete_user(userId):
    utils.delete_user_from_db(userId)
    return "OK", 200

@app.route('/api/v1/delete_users', methods=['DELETE'])
@login_required
def delete_users():
    utils.delete_users_from_db()
    return "OK", 200

@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500

def checkIfAdminUser():
    user = utils.get_user_from_db(current_user.identity)
    if user.type == "User":
        return False
    else:
        return True

@app.context_processor
def utility_functions():

    def print_in_console(message):
        print str(message)

    def str_to_obj(str):
        return eval(str)

    def get_current_date():
        import datetime
        return datetime.date.today().strftime("%Y-%m-%d")

    def get_current_user():
        cu = {"identity": current_user.identity.decode('unicode_escape').encode('ascii','ignore'),
              "email": current_user.email.decode('unicode_escape').encode('ascii','ignore'),
              "password": current_user.password.decode('unicode_escape').encode('ascii','ignore')}
        return cu

    @app.template_filter('urlencode')
    def urlencode_filter(s):
        if type(s) == 'Markup':
            s = s.unescape()
        s = s.encode('utf8')
        s = urllib.quote(s)
        return Markup(s)

    app.jinja_env.globals['urlencode'] = urlencode_filter
    return dict(get_current_user=get_current_user,
                urlencode=urlencode_filter,
                mdebug=print_in_console,
                str_to_obj=str_to_obj,
                get_current_date=get_current_date)

# [END app]
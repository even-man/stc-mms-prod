from functools import wraps
from flask import Flask, render_template, flash, redirect, url_for, session, request
import sqlite3
from setup import SecretKey, DatabasePath
import datetime

#app setup
app = Flask(__name__)
app.secret_key = SecretKey()

#database setup
DB_PATH = DatabasePath()


#user authentication for controlling routing
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            session['messages'] = 'Login to access this resource.'
            return redirect(url_for('home'))
    return wrap


# home route : GET and POST
# GET
#   renders home.html template
# POST
#   gets data from forms and logs user in if appropriate
#   sets session
@app.route("/", methods = ['GET', 'POST'])
def home():
    if request.method == 'GET':
        return render_template("home.html")
    if request.method == 'POST':

        username = request.form['UserName']
        password = request.form['Password']

        sql = 'SELECT * FROM admins'
        data = sql_data_to_list_of_dicts(DB_PATH, sql)

        loginStatus = login(data, username, password)

        if loginStatus:
            session['logged_in'] = True
            session['username'] = username

            return redirect(url_for('dashboard'))
        
        else:
            message = 'Invalid Login'
            return render_template('home.html', message=message)


#dict for standing filter
standingFilters = {
    'GoodStanding' : 'Good Standing',
    'FacilityBanSemester' : 'Facility Ban (Semester)',
    'PermaBan' : 'PermaBan',
    'CheckoutBanMonth' : 'Checkout Ban (One Month)',
    'RecordedUsers' : 1
}


# dashboard route : GET
# GET
#   returns the dashboard.html template IF user logged in
@app.route('/dashboard', methods=['GET', 'POST'])
@is_logged_in
def dashboard():
    session['messages'] = str()

    if request.method == 'GET':
        return render_template('dashboard.html')
    
    if request.method == 'POST':
        
        username = request.form.get('username')
        numbermarks = request.form.get('numbermarks')
        reason = request.form.get('reason')
        issuer = request.form.get('issuer')
        date = datetime.date.today().strftime('%Y-%m-%d')
        
        error = 'All inputs must contain info'
        message = 'Marks successfully entered'

        if username == '' or reason == '' or issuer == '' or numbermarks == '':
            return render_template('dashboard.html', error = error)
        
        data = search_by_username(username)

        if len(data) == 0:
            insert_user_and_marks(username, numbermarks, date, reason, issuer)
            return render_template('dashboard.html', message = message)
        else:
            currentMarksTotal = data[0]['NumberMarks']
            app.logger.info(currentMarksTotal)

            update_user_insert_marks(username, numbermarks, date, reason, issuer, currentMarksTotal)


            return render_template('dashboard.html', message=message)

# users route : GET POST
# GET
#   returns a form for filtering users and searching by username

@app.route('/users', methods = ['GET', 'POST'])
@is_logged_in
def users():
    
    if request.method == 'GET':
        return render_template('users.html')
    if request.method == 'POST':

        value1 = request.form.get('Users')
        app.logger.info(f'Users Value from form: {value1}')


        if request.form.get('Users') == 'standingForm':
            app.logger.info('standing form submitted')

            standing = request.form['standings']
            app.logger.info(f'standing filter: {standing}')

            sql = f'SELECT * FROM Users WHERE CurrentStanding == "{standingFilters[standing]}"'

            app.logger.info(f'sql: {sql}')

            data = sql_data_to_list_of_dicts(DB_PATH, sql)
            
            return render_template('users.html', data=data)

        if request.form.get('Users') == 'usernameForm':
            app.logger.info('username search form submitted')

            username = request.form['username']
            app.logger.info(f'username: {username}')

            sql = f'SELECT * FROM Users WHERE UserName == "{username}"'
            data = sql_data_to_list_of_dicts(DB_PATH, sql)

            return render_template('users.html', data=data)

@app.route('/marks', methods=['GET', 'POST'])
@is_logged_in
def marks():
    session['messages'] = str()

    if request.method == 'GET':
        return render_template('marks.html')
    if request.method == 'POST':

        if request.form.get('marks') == 'usernameFilter':
            #search by username
            username = request.form['username']
            sql = f'SELECT * FROM Marks WHERE UserName = "{username}"'
            data = sql_data_to_list_of_dicts(DB_PATH, sql)
            return render_template('marks.html', data=data)

        if request.form.get('marks') == 'refresh':
            #return all data
            sql = f'SELECT * FROM Marks'
            data = sql_data_to_list_of_dicts(DB_PATH, sql)
            return render_template('marks.html', data=data)


# about route : GET
# GET
#   returns the about.html template
@app.route("/about")
def about():
    session['messages'] = str()
    return render_template("about.html")

# logout route : POST
# POST
#   gets data from form by js script on _navbar.html 
#   IF userInput TRUE, clear session and redirect home
#   ELSE redirect to dashboard

@app.route("/logout", methods=['GET', 'POST'])
def logout():
     session.clear()
     return redirect(url_for('home'))


@app.route("/update/<string:username>", methods = ['GET', 'POST'])
@is_logged_in
def update(username):
    session['messages'] = str()

    if request.method == 'GET':

        data = sql_data_to_list_of_dicts(DB_PATH, f'SELECT * FROM Users WHERE UserName = "{username}"')
        date = datetime.date.today().strftime('%Y-%m-%d')

        return render_template('update.html', data=data, date=date)

    if request.method == 'POST':

        if request.form.get('formUpdate') == 'submitForm':

            username = request.form.get('username')
            numbermarks = request.form.get('numbermarks')
            date = datetime.date.today().strftime('%Y-%m-%d')

            update_user(username, numbermarks, date)

            session['messages'] = 'User successfully updated'
            return redirect(url_for('users'))

        if request.form.get('formUpdate') == 'cancelForm':
            return redirect(url_for('users'))


@app.route('/delete/<string:username>', methods = ['GET', 'POST'])
@is_logged_in
def delete(username):
    session['messages'] = str()

    if request.method == 'GET':
        data = sql_data_to_list_of_dicts(DB_PATH, f'SELECT * FROM Users WHERE UserName = "{username}"')
        return render_template('delete.html', data=data)

    if request.method == 'POST':
        if request.form.get('DeleteForm') == 'submitDelete':
            delete_user(username)
            session['messages'] = 'User successfully deleted'
            return redirect(url_for('users'))
        if request.form.get('DeleteForm') == 'cancelDelete':
            return redirect(url_for('users'))


@app.route('/manage', methods = ['POST', 'GET'])
@is_logged_in
def manage():

    summaries = sql_data_to_list_of_dicts(DB_PATH, f'SELECT * FROM Summaries')

    if request.method == 'GET':
        if session['username'] != 'stcmanage':
            session['messages'] = 'Login to access this resource'
            return redirect(url_for('home'))
        else:
            return render_template('manage.html', summaries = summaries)
    
    if request.method == 'POST':

        # reset form
        if request.form.get('Manage') == 'resetForm':
            if request.form.get('confirmReset') == 'on':
                date = datetime.date.today().strftime('%Y-%m-%d')
                reset_users(date)
                session['messages'] = 'Users reset.'
                return render_template('manage.html', summaries = summaries)
            if request.form.get('confirmReset') != 'on':
                app.logger.info('Check is not on')
                return render_template('manage.html', error = 'Press check to reset users', summaries = summaries)

        # standing form     
        if request.form.get('Manage') == 'standingForm':
            standing = request.form.get('standings') 
            filter = standingFilters[standing]

            if standing == 'RecordedUsers':
                sql = f'SELECT * FROM Users WHERE Recorded == 1'
                filter = 'recorded users'
            else:
                sql = f'SELECT * FROM Users WHERE CurrentStanding == "{filter}" AND Recorded = 0'
            
            users = sql_data_to_list_of_dicts(DB_PATH, sql)
            app.logger.info(sql)

            return render_template('manage.html', users = users, filter=filter)
        


@app.route('/record/<string:user>/<string:record>', methods=['GET', 'POST'])
@is_logged_in
def record(user, record):
    update_recorded(user, record)
    return redirect(url_for('manage'))




# DATA ACCESS METHODS #

# get sql data and return as dict object  
def sql_data_to_list_of_dicts(path_to_db, select_query):

    try:
        con = sqlite3.connect(path_to_db)
        con.row_factory = sqlite3.Row
        things = con.execute(select_query).fetchall()
        unpacked = [{k: item[k] for k in item.keys()} for item in things]
        return unpacked
    except Exception as e:
        print(f"Failed to execute. Query: {select_query}\n with error:\n{e}")
        return []
    finally:
        con.close()

# check user accounts for provided username, password candidates
def login(data, username, password):
    for item in data:
        if item['Password'] == password and item['UserName'] == username:
                 return True
    return False

def search_by_username(username):
    sql = f'SELECT * FROM Users WHERE UserName == "{username}"'
    data = sql_data_to_list_of_dicts(DB_PATH, sql)
    return data

def insert_user_and_marks(username, numbermarks, date, reason, issuer):
    sql_insert_new_user = f'INSERT INTO Users(UserName, CurrentStanding, NumberMarks, RecentDate, Recorded) values("{username}", "{standing_resolver(numbermarks)}",{numbermarks},"{date}", 0)'
    sql_insert_new_marks = f'INSERT INTO Marks(UserName, NumberMarks, Reason, Date, Issuer) values("{username}", {numbermarks}, "{reason}", "{date}", "{issuer}")'

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(sql_insert_new_user)
    cur.execute(sql_insert_new_marks)

    conn.commit()
    conn.close()

def standing_resolver(numbermarks):
    if int(numbermarks) <= 15:
        return 'Good Standing'
    if int(numbermarks) > 15 and int(numbermarks) < 30:
        return 'Checkout Ban (One Month)'
    if int(numbermarks) >= 30 and int(numbermarks) < 999:
        return 'Facility Ban (Semester)'
    if int(numbermarks) >= 999:
        return 'PermaBan'

def update_user_insert_marks(username, numbermarks, date, reason, issuer, currentMarksTotal):


    sql_insert_new_marks = f'INSERT INTO Marks(UserName, NumberMarks, Reason, Date, Issuer) values("{username}", {numbermarks}, "{reason}", "{date}", "{issuer}")'
    sql_update_user = f'UPDATE Users SET NumberMarks = "{int(numbermarks) + int(currentMarksTotal)}", CurrentStanding = "{standing_resolver(int(numbermarks) + int(currentMarksTotal))}", RecentDate = "{date}" WHERE UserName = "{username}"'

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(sql_insert_new_marks)
    cur.execute(sql_update_user)

    conn.commit()
    conn.close()

def update_user(username, numbermarks, date):
    sql_update_user = f'UPDATE Users SET NumberMarks = "{numbermarks}", UserName = "{username}", RecentDate = "{date}", CurrentStanding = "{standing_resolver(int(numbermarks))}" WHERE UserName = "{username}"'
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(sql_update_user)
    conn.commit()
    conn.close()

def delete_user(username):
    sql_delete_user = f'DELETE FROM Users WHERE UserName = "{username}"'
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(sql_delete_user)
    conn.commit()
    conn.close()

def reset_users(date):
    sql_reset_users = f'UPDATE Users SET NumberMarks = 0, CurrentStanding = "Good Standing", Recorded = 0, RecentDate = "{date}" WHERE CurrentStanding != "PermaBan"'
    sql_reset_summaries = f'UPDATE Summaries SET Value = 0 WHERE Field = "TotalMarks"'
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(sql_reset_users)
    cur.execute(sql_reset_summaries)
    conn.commit()
    conn.close()

def update_recorded(username, record):

    record = int(record)
    if record == 0:
        newRecordValue = 1
    else:
        newRecordValue = 0

    sql = f'UPDATE Users SET Recorded = {newRecordValue} WHERE UserName = "{username}"'
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    conn.close()

    

# RUN APP #

if __name__ == '__main__':
    app.run(debug = True, host='0.0.0.0')
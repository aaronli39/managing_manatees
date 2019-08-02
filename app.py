import json
import datetime
from os import urandom
from traceback import print_exc

from flask import Flask, request, render_template, redirect, flash, session
from util import Database

ALLOWED_EXTENSIONS = {'csv'}
REPL_MODE = False

config = json.load(open("config/mongo.json"))

app = Flask(__name__)

app.config["MONGO_DBNAME"] = config['databaseName']
app.config["MONGO_URI"] = config['mongoURI']
app.config["SECRET_KEY"] = b'J\x94":\x07eI\x8d\xe1(/\x16O\x08\xc8\xb4C1xDowKq\x03E\xc5^\xd3\xfe\xba\x03'

dbtools = Database.DBTools(app)


def redirectByUserType(userType):
    if userType == 'admin':
        return redirect('/admin')
    elif userType == 'student':
        return redirect('/student')
    elif userType == 'teacher':
        return redirect('/teacher')


@app.route("/")
def index():
    if 'username' in session:
        return redirectByUserType(session['userType'])
    return render_template("landing.html")


@app.route("/login", methods=["GET", "POST"])
def log():
    if 'username' in session:
        return redirectByUserType(session['userType'])
    if request.method == "GET":
        return render_template('login.html')
    inputPass = request.form['pass']
    inputUsername = request.form['username']
    if request.form['schoolid'] == '':  #Admin login
        if dbtools.authAdmin(inputUsername, inputPass):
            session['username'] = inputUsername
            session['userType'] = 'admin'
            return redirect('/admin')
        else:
            flash('Invalid username or password.')
    else:
        if dbtools.authStudent(request.form['schoolid'], inputUsername, inputPass):
            session['username'] = inputUsername
            session['userType'] = 'student'
            session['schoolID'] = request.form['schoolid']
            return redirect('/student')
        elif dbtools.authTeacher(request.form['schoolid'], inputUsername, inputPass):
            session['username'] = inputUsername
            session['userType'] = 'teacher'
            session['schoolID'] = request.form['schoolid']
            return redirect('/teacher')
        else:
            flash('invalid username or password.')
    return render_template('login.html')


@app.route("/register", methods=['GET', 'POST'])
def reg():
    if request.method == 'GET':
        return render_template("register.html")
    inputPass = request.form['pass']
    passConfirm = request.form['passConfirm']
    inputUsername = request.form['username']
    if passConfirm != inputPass:
        flash('Passwords do not match!')
    else:
        msg = dbtools.registerAdmin(inputUsername, inputPass)
        flash(msg)
        if msg == 'Registration successful.':
            return redirect('/login')
    return render_template('register.html')


@app.route("/uploadStudentCSV", methods=['POST'])
def uploadStudentCSV():
    if 'username' not in session:
        return redirect('/login')
    if session['userType'] != 'admin':
        flash('You are not a administrator!')
        return redirectByUserType(session['userType'])
    if 'inputCSV' not in request.files:
        flash('No file part')
        return redirect(request.referrer)
    inputFile = request.files['inputCSV']
    if inputFile.filename == '':
        flash('No file uploaded')
        return redirect(request.referrer)
    if inputFile.filename.rsplit('.', 1)[1].lower() != 'csv':
        flash('Invalid file type')
        return redirect(request.referrer)
    csv = inputFile.read().decode('utf-8')
    flash(
        dbtools.addStudentsFromCSV(session['username'],
                                   request.form['schoolID'], csv))
    return redirect(request.referrer)


@app.route("/admin")
def admin():
    if 'username' not in session:
        return redirect('/login')
    return render_template("admin_home.html",
                           username=session['username'],
                           managed=dbtools.getBasicSchoolInfo(
                               session['username']))


@app.route('/student')
def student():
    if 'username' not in session:
        return redirect('/login')
    studentInfo = dbtools.getStudentInfoByUsername(session['schoolID'], session['username'])
    classIDs = studentInfo["classes"]
    ret = []
    for i in classIDs:
        classData = dbtools.getClassInfo(session["username"], session["schoolID"], i)
        ret.append(classData["className"])
    return render_template("student.html", classes = ret, schoolID = session["schoolID"], classID = classIDs, name = studentInfo['name'][0])


@app.route('/changePass', methods=['POST'])
def changePass():
    if 'username' not in session:
        return redirect('/login')
    if session['userType'] == 'student' or session['userType'] == 'teacher':
        if dbtools.authStudent(
                session['schoolID'], session['username'],
                request.form['oldPassword']) or dbtools.authTeacher(
                    session['schoolID'], session['username'],
                    request.form['oldPassword']):
            flash(
                dbtools.changePassword(session['username'],
                                       request.form['newPassword'],
                                       session['schoolID']))
        else:
            flash("Incorrect password")
    elif session['userType'] == 'admin':
        if dbtools.authAdmin(session['username'], request.form['oldPassword']):
            flash(
                dbtools.changePassword(session['username'],
                                       request.form['newPassword']))
        else:
            flash("Incorrect password")
    return redirect(request.referrer)


@app.route("/createSchool", methods=["POST"])
def createClass():
    if 'username' not in session:
        return redirect('/login')
    if session['userType'] != 'admin':
        flash('You are not a administrator!')
        return redirectByUserType(session['userType'])
    if request.form['schoolName'] == '':
        flash('No school name given')
        return redirect('/admin')
    dbtools.registerSchool(session['username'], request.form['schoolName'])
    flash('Registration successful')
    return redirect('/admin')


@app.route("/school/<schoolID>")
def schoolPage(schoolID):
    if 'username' not in session:
        return redirect('/login')
    if session['userType'] != 'admin':
        return redirectByUserType(session['userType'])
    if not (dbtools.checkAdmin(schoolID, session['username'])):
        flash('You are not a administrator of this school!')
        return redirectByUserType(session['userType'])
    return render_template("schools.html",
                           schoolData=dbtools.getSchoolInfo(schoolID),
                           username=session['username'])


@app.route('/addClass', methods=['POST'])
def addClass():
    if 'username' not in session:
        return redirect('/login')
    if session['userType'] != 'admin':
        flash('You are not a administrator!')
        return redirectByUserType(session['userType'])
    flash(
        dbtools.addClass(session['username'], request.form['schoolID'],
                         request.form['className']))
    return redirect(request.referrer)


@app.route('/deleteSchool/<schoolID>')
def deleteSchool(schoolID):
    if 'username' not in session:
        return redirect('/login')
    if session['userType'] != 'admin':
        flash('You are not a administrator!')
        return redirectByUserType(session['userType'])
    flash(dbtools.deleteSchool(session['username'], schoolID))
    return redirect('/admin')


@app.route('/logout')
def logout():
    if 'username' in session:
        session.pop('username')
        session.pop('userType')
    return redirect('/')


@app.route('/school/<schoolID>/class/<classID>')
def classRoute(schoolID, classID):
    if 'username' not in session:
        return redirect('/login')
    if session['userType'] == 'admin' and not dbtools.checkAdmin(schoolID, session['username']):
        flash("You are not a administrator of this school!")
        return redirect('/admin')
    classData = dbtools.getClassInfo(session["username"], schoolID, classID)
    if classData == None:
        flash("This class does not exist!")
        return redirectByUserType(session['userType'])
    if session['userType'] == 'teacher' and classData['teacher'] != session['username']:
        flash("You are not a teacher of this class!")
        return redirect('/teacher')
    if session['userType'] == 'student':
        studentInfo = dbtools.getStudentInfoByUsername(schoolID, session['username'])
        if classData['classID'] not in studentInfo['classes']:
            flash("You are not enrolled in this class!")
            return redirect('/student')
    return render_template('class.html', schoolID = schoolID, classData = classData,
                            isTeacher = session['userType'] == 'admin' or session['userType'] == 'teacher',
                            getTeacherInfo = dbtools.getTeacherInfo, getStudentInfo = dbtools.getStudentInfo, classID = classID)

@app.route('/addAdmin', methods=['POST'])
def addAdmin():
    if 'username' not in session:
        return redirect('/login')
    if session['userType'] != 'admin':
        flash('You are not a administrator!')
        return redirectByUserType(session['userType'])
    flash(
        dbtools.addAdmin(session['username'], request.form['schoolID'],
                         request.form['adminUsername']))
    return redirect(request.referrer)

@app.route('/teacher')
def teacher():
    if 'username' not in session:
        return redirect('/login')
    teacherInfo = dbtools.getTeacherInfo(session['schoolID'], session['username'])
    classIDs = teacherInfo["classes"]
    ret = []
    for i in classIDs:
        classData = dbtools.getClassInfo(session["username"], session["schoolID"], i)
        ret.append(classData["className"])
    return render_template("teacher.html", classes = ret, schoolID = session["schoolID"], classID = classIDs, name = teacherInfo['name'][0])

@app.route("/addStu", methods=["POST"])
def addStud():
    if 'username' not in session:
        return redirect('/')
    if session['userType'] != 'admin' and session['userType'] != 'teacher':
        flash("User is not a teacher or admin of this class")
        return redirect(request.referrer)
    student = request.form.get("studentID")
    schoolID = request.form.get("schoolID")
    classID = request.form.get("classID")
    dbtools.addStudentClass(session['username'], schoolID, student, classID)
    flash("Student added to class")
    return redirect("/school/" + str(schoolID))


@app.route('/makepost/<schoolID>/<classID>')
def makePost(classID, schoolID):
    if 'username' not in session:
        return redirect('/')
    if session['userType'] != 'admin' and session['userType'] != 'teacher':
        flash("User is not a teacher or admin of this class")
        return redirect(request.referrer)
    date = str(datetime.date.today())
    return render_template("makepost.html",
                           date=date,
                           classID=classID,
                           schoolID=schoolID)


@app.route('/processmakepost/<schoolID>/<classID>', methods=['POST'])
def processMakePost(schoolID, classID):
    if 'username' not in session:
        return redirect('/')
    if session['userType'] != 'admin' and session['userType'] != 'teacher':
        flash("User is not a teacher or admin of this class")
        return redirect(request.referrer)
    postTitle = request.form['postTitle']
    postbody = request.form['postbody']
    postbody = postbody.replace('<br>', ' ')  #Replace new lines with a space
    postbody = postbody.replace(
        '<div>', ' ')  #Same as above, used for compatability among browsers
    postbody = postbody.replace('</div>', '')
    duedate = None
    due = "Never"
    dueCheck = False
    if 'setDueDate' in request.form:
        dueCheck = True
    if dueCheck:  #Will insert a due date if the checkbox is checked
        duedate = request.form['duedate']
        duetime = request.form['duetime']
        due = duedate + " " + duetime
    dbtools.makePost(schoolID, classID, due, postbody, postTitle)
    #starttime = str(db.get_start_time(postID))
    # if dueCheck:
    #     event = {
    #         'summary': postTitle,
    #         'description': request.form['postbody'],
    #         'start': {
    #             'date': str(datetime.date.today()),
    #             #'dateTime': '2019-01-10T09:00:00-07:00',
    #             'timeZone': 'America/New_York',
    #         },
    #         'end': {
    #             'date': duedate,
    #             #'dateTime': '2019-01-19T17:00:00-07:00',
    #             'timeZone': 'America/New_York',
    #         }
    #         #'start.date': str(datetime.date.today()),
    #         #'end.date': str(duedate),
    #     }
    #     #json_event = json.loads(event)
    return redirect('/school/' + schoolID + '/class/' + classID)


if __name__ == "__main__":
    if REPL_MODE:
        while True:
            try:
                userInput = input('>>> ')
                if userInput == 'quit':
                    break
                print(eval(userInput))
            except KeyboardInterrupt:
                print()
                break
            except:
                print_exc()
    else:
        app.debug = True
        app.run()

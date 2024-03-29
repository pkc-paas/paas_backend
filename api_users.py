# api_users.py

from typing import Optional, List
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi import HTTPException, Header
import secrets, bcrypt, datetime

from paas_launch import app
import commonfuncs as cf
import dbconnect
from api_email import sendEmail


rolesList = ['admin','moderator','sponsor','saplings_admin','saplings_entry']
EMAILS_UNIQUE = False

def encrypt(password):
    salt = bcrypt.gensalt()
    hash_string = bcrypt.hashpw(password.encode('utf-8'), salt).decode()
    return hash_string


def decrypt(hash_string,pwd):
    if bcrypt.checkpw(pwd.encode('utf-8'), hash_string.encode('utf-8')):
        return True
    else:
        return False


def authenticate(token, allowed_roles=['admin']):
    s1 = f"""select t1.username, t2.role
    from sessions as t1
    left join users as t2
    on t1.username = t2.username
    where t1.token = '{token}'
    """
    #s1 = f"select username, role from users where token='{token}'"

    user = dbconnect.makeQuery(s1, output='oneJson', printit=False)
    if not user:
        cf.logmessage(f"rejected")
        raise HTTPException(status_code=401, detail="Invalid login")
    if len(allowed_roles):
        if user.get('role') not in allowed_roles:
            cf.logmessage(f"Insufficient permissions")
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user['username'], user['role']


def findRole(token):
    # s1 = f"select username, role from users where token='{token}'"
    s1 = f"""select t1.username, t2.role
    from sessions as t1
    left join users as t2
    on t1.username = t2.username
    where t1.token = '{token}'
    """
    user = dbconnect.makeQuery(s1, output='oneJson', printit=False)
    if not user:
        return None, None
    else:
        return user['username'], user['role']

########################

class loginRBody(BaseModel):
    username: str
    pw: str

@app.post("/API/login", tags=["users"])
def login(r: loginRBody, X_Forwarded_For: Optional[str] = Header(None)):
    cf.logmessage(f"login POST api call")
    s1 = f"select email, username, pwd, status from users where username='{r.username}'"
    row = dbconnect.makeQuery(s1, output='oneJson')
    if not row:
        raise HTTPException(status_code=401, detail="Invalid username")
    
    # check password
    if not decrypt(row['pwd'], r.pw):
        cf.logmessage(f"rejected")
        raise HTTPException(status_code=401, detail="Invalid login")
    
    if not X_Forwarded_For: 
        X_Forwarded_For = ''

    if row['status']:
        if row['status'] not in ('APPROVED'):
            raise HTTPException(status_code=403, detail="User is not approved yet")

    cf.logmessage(f"user {row['username']} authenticated")
    token = secrets.token_urlsafe(25)
    i1 = f"""insert into sessions (token, username, ip, created_on) values 
    ('{token}','{row['username']}', '{X_Forwarded_For[:50]}', CURRENT_TIMESTAMP)
    """
    iCount = dbconnect.execSQL(i1)
    
    returnD = {
        "message": "Successfully logged in user",
        "token": token,
        "email": row['email'],
        "username": row['username']
    }

    return returnD    

########################

class changePwBody(BaseModel):
    username: str
    # email: str
    oldpw: str
    newpw: str

@app.post("/API/changepw", tags=["users"])
def changepw(r: changePwBody, X_Forwarded_For: Optional[str] = Header(None)):
    cf.logmessage(f"changepw POST api call")
    s1 = f"select * from users where username='{r.username}'"
    row = dbconnect.makeQuery(s1, output='oneJson')
    if not row:
        raise HTTPException(status_code=401, detail="Invalid username")
    
    if not decrypt(row['pwd'], r.oldpw):
        cf.logmessage(f"rejected")
        raise HTTPException(status_code=401, detail="Invalid login")

    new_password = encrypt(r.newpw)
    u1 = f"""update users
    set pwd = '{new_password}'
    where username='{r.username}'
    """
    status = dbconnect.execSQL(u1)

    # also clearing all existing sessions
    d1 = f"delete from sessions where username = '{r.username}"
    status2 = dbconnect.execSQL(d1)

    returnD = {
        "message": "password changed successfully. Pls login with new password."
    }
    return returnD


########################

@app.get("/API/logout", tags=["users"])
def logout(x_access_key: Optional[str] = Header(None)):
    cf.logmessage("logout api call")
    
    d1 = f"delete from sessions where token='{x_access_key}'"
    uCount = dbconnect.execSQL(d1)
    
    if not uCount:
        cf.logmessage("db error when logging out, but telling frontend to logout out anyways")
    
    returnD = {"message":"Logged out"}
    return returnD

########################

@app.get("/API/checkUser", tags=["users"])
def checkUser(x_access_key: Optional[str] = Header(None)):
    cf.logmessage("checkUser api call")
    try:
        username, role = authenticate(x_access_key, allowed_roles=[])
    except:
        username, role = None, None
    cf.logmessage(f"user: {username} role: {role}")
    returnD = {"message":"", "username":username, "role":role }
    return returnD


########################


class createUser_payload(BaseModel):
    username: str
    role: str
    pwd: str
    email: str
    fullname: Optional[str]
    remarks: Optional[str]

@app.post("/API/createUser", tags=["users"])
def createUser(req: createUser_payload, x_access_key: Optional[str] = Header(None), X_Forwarded_For: Optional[str] = Header(None)):
    cf.logmessage("createUser api call")

    username, role = authenticate(x_access_key, allowed_roles=['admin'])
    
    s1 = f"select username from users where username = '{req.username}'"
    exist = dbconnect.makeQuery(s1, output="oneValue")
    if exist:
        raise HTTPException(status_code=406, detail="This username is already taken")
        
    hash_string = encrypt(req.pwd)
    i1 = f"""insert into users (username, email, role, pwd, fullname, `status`, created_by, created_on) values
    ('{req.username}','{req.email}','{req.role}','{hash_string}','{req.username}', 'APPROVED', '{username}',CURRENT_TIMESTAMP)
    """
    # since admin is doing it, auto-approve
    
    cf.logmessage(f"Creating user {req.username} {req.role} {req.email}")
    iCount = dbconnect.execSQL(i1, noprint=True)
    
    # to do: send automated emails

    returnD = {'status':'success'}
    if iCount:
        returnD['added_count'] = iCount
        return returnD
    else:
        raise HTTPException(status_code=500, detail="Failed to insert new user entry")


########################



@app.get("/API/listUsers", tags=["users"])
def listUsers( x_access_key: Optional[str] = Header(...)):
    cf.logmessage("listUsers api call")
    username, role = authenticate(x_access_key, allowed_roles=['admin'])

    s1 = f"""select username, email, role, fullname, remarks, status,
    last_login, created_on, created_by, last_pw_change
    from users
    order by created_on desc
    """
    uList = dbconnect.makeQuery(s1, output='list')
    returnD = {'status':'success'}
    returnD['data'] = uList
    returnD['count'] = len(uList)

    return returnD


########################


class signup_payload(BaseModel):
    username: str
    email: str
    pwd: str
    role: str
    # phone: str
    fullname: str
    referral: Optional[str] 
    remarks: Optional[str]

@app.post("/API/signup", tags=["users"])
def signup(req: signup_payload, X_Forwarded_For: Optional[str] = Header(None)):
    cf.logmessage("signup api call")

    # Validations

    # username should be unique
    c1 = f"select count(username) from users where username='{req.username}'"
    existing = dbconnect.makeQuery(c1)
    if existing != 0:
        raise HTTPException(status_code=406, detail="This username already exists in the system, please use another")

    global rolesList
    if req.role not in rolesList:
        raise HTTPException(status_code=400, detail="Invalid role")


    iCols = []
    iVals = []

    # validation: check if same email already existing, if we are set to keep emails unique
    global EMAILS_UNIQUE
    if EMAILS_UNIQUE:
        s2 = f"select count(email) from users where email = '{req.email}' and status in ('APPROVED','APPLIED')"
        emailCount = dbconnect.makeQuery(s2, output='oneValue')
        if emailCount:
            raise HTTPException(status_code=406, detail="This email is already registered")



    # check referral code, determine status based on that
    status = 'APPLIED'
    refCount = 0
    if req.referral:
        s1 = f"""SELECT count(*) FROM referral_codes 
        WHERE referral_code = '{req.referral}' 
        and CURRENT_TIMESTAMP <= valid_upto
        """
        refCount = dbconnect.makeQuery(s1, output='oneValue')

        if refCount > 0:
            cf.logmessage("Referral code verified, fast-track!")
            status = 'APPROVED'
            iCols.append('referral_code')
            iVals.append(f"'{req.referral}'")
        else:
            cf.logmessage("Invalid referral code, error out")
            raise HTTPException(status_code=400, detail="Invalid referral code")
    
    hash_string = encrypt(req.pwd)
    iCols.append('pwd')
    iVals.append(f"'{hash_string}'")

    iCols.append('status')
    iVals.append(f"'{status}'")

    iCols.append('username')
    iVals.append(f"'{req.username}'")

    iCols.append('email')
    iVals.append(f"'{req.email}'")

    iCols.append('role')
    iVals.append(f"'{req.role}'")

    iCols.append('fullname')
    iVals.append(f"'{req.fullname}'")

    if req.remarks:
        iCols.append('remarks')
        iVals.append(f"'{req.remarks}'")

    iCols.append('created_on')
    iVals.append(f"CURRENT_TIMESTAMP")

    iCols.append('created_by')
    iVals.append(f"'SIGNUP'")

    if not X_Forwarded_For:
        X_Forwarded_For = ''
    iCols.append('creator_ip')
    iVals.append(f"'{X_Forwarded_For[:50]}'")

    i1 = f"""insert into users ({','.join(iCols)}) values ({','.join(iVals)})
    """
    i1Count = dbconnect.execSQL(i1)
    if not i1Count:
        raise HTTPException(status_code=500, detail="Unable to create entry in DB, please contact Admin")

    returnD = {'status':'success'}

    if status == 'APPROVED':
        returnD['auto'] = True
    else:
        returnD['auto'] = False

    return returnD


#########

@app.get('/API/usernameAvailable', tags=["users"])
def usernameAvailable(username: str, X_Forwarded_For: Optional[str] = Header(None)):
    # to do: other validations

    # might want to bring in rate-limiting for this one

    reservedList = ['admin','superadmin']
    if username in reservedList:
        return {'status':False }

    c1 = f"select count(username) from users where username='{username}'"
    existing = dbconnect.makeQuery(c1, output='oneValue')
    if existing != 0:
        return {'status':False }
    else:
        return {'status':True }

##########

@app.get("/API/forgotPw_trigger", tags=["users"])
def forgotPw_trigger(username, X_Forwarded_For: Optional[str] = Header(None)):
    cf.logmessage("forgotPw_trigger api call")
    # check if valid username
    s1 = f"select username, email from users where username='{username}'"
    row = dbconnect.makeQuery(s1, output='oneJson')

    if not row:
        raise HTTPException(status_code=400, detail="Invalid username")

    txnid = secrets.token_urlsafe(25)

    # make OTP, from https://docs.python.org/3/library/secrets.html
    otp = 1000 + secrets.randbelow(9000)
    validity = 30 # mins the OTP is valid for
    if not X_Forwarded_For:
        X_Forwarded_For = ''

    i1 = f"""insert into otps (txnid, otp, created_for, purpose, validity, ip) values (
    '{txnid}', {otp}, '{username}', 'forgotPw', {validity}, '{X_Forwarded_For[:50]}'
    )"""
    i1Count = dbconnect.execSQL(i1)
    if not i1Count:
        cf.logmessage("Warning: Unable to insert into otps table")
        raise HTTPException(status_code=500, detail="Sorry, could not trigger OTP for some reason; pls try again after 10 mins or contact admin.")

    # trigger OTP email
    subject = f"{otp} is the OTP for ConnecTree password reset for user {username}"
    content = subject
    html = f"""<b>{otp}</b> is the OTP for ConnecTree password reset for user <b>{username}</b>.
    <br><br><br>
    Note: This OTP will expire in {validity} mins.<br>
    This is an auto-generated email from the ConnecTree website. In case this doesn't apply to you, then please ignore this.
    """

    status = sendEmail(content=content, subject=subject, recipients=[row['email']], cc=None, html=html)
    if len(status.keys()):
        cf.logmessage(status)
        cf.logmessage("Warning: Might have been unable to send OTP email, printing in logs and proceeding")
        cf.logmessage(f"user: {username}, txnid: {txnid}, OTP:{otp}")
    
    return {'txnid': txnid, 'otpMethod': 'email' }


##########

class resetPw_payload(BaseModel):
    txnid: str
    otp: int
    newpw: str

@app.post("/resetPw", tags=["users"])
def forgotPw_trigger(req: resetPw_payload, X_Forwarded_For: Optional[str] = Header(None)):
    cf.logmessage("resetPw api call")
    if not X_Forwarded_For:
        X_Forwarded_For = ''

    s1 = f"""select t1.*, t2.email
    from otps as t1
    left join users as t2
    on t1.created_for = t2.username
    where t1.txnid='{req.txnid}'"""
    row = dbconnect.makeQuery(s1, output="oneJson")

    if not row:
        raise HTTPException(status_code=400, detail=f"Invalid txnid")
    if req.otp != row['otp']:
        raise HTTPException(status_code=401, detail=f"Invalid otp")
    ## http status codes: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status

    if not row['email']:
        raise HTTPException(status_code=400, detail=f"Invalid user")

    # don't allow if too late
    # row['created_on'] is already in pandas timestamp format, can be used as datetime obj
    tdiff = (datetime.datetime.utcnow() - row['created_on']).total_seconds()/60
    if tdiff > row['validity']:
        raise HTTPException(status_code=401, detail=f"Sorry, the OTP has expired. Please trigger again.")
    
    # ok all clear now. Validate new pw
    # to do - validation by chars etc
    
    new_password = encrypt(req.newpw)
    u1 = f"""update users 
    set pwd = '{new_password}',
    last_pw_change = CURRENT_DATE
    where username = '{row['created_for']}'"""
    u1Count = dbconnect.execSQL(u1)

    # to do: formality: send another email

    return {'status':'success'}


###############

class approveUsers_payload(BaseModel):
    usersList: List[str]

@app.post("/API/approveUsers", tags=["users"])
def listUsers(req: approveUsers_payload, x_access_key: Optional[str] = Header(...)):
    cf.logmessage("approveUsers api call")
    username, role = authenticate(x_access_key, allowed_roles=['admin'])

    usersListSQL = cf.quoteNcomma(req.usersList)
    u1 = f"""update users
    set status = 'APPROVED'
    where username in ({usersListSQL})
    and ( status = 'APPLIED'
    or status is NULL) """

    u1Count = dbconnect.execSQL(u1)

    returnD =  {'status':'success', 'count':u1Count }
    return returnD


#######

class revertUsers_payload(BaseModel):
    usersList: List[str]

@app.post("/API/revertUsers", tags=["users"])
def listUsers(req: revertUsers_payload, x_access_key: Optional[str] = Header(...)):
    cf.logmessage("revertUsers api call")
    username, role = authenticate(x_access_key, allowed_roles=['admin'])

    usersListSQL = cf.quoteNcomma(req.usersList)
    u1 = f"""update users
    set status = 'APPLIED'
    where username in ({usersListSQL})
    and ( status = 'APPROVED'
    or status is NULL) """

    u1Count = dbconnect.execSQL(u1)

    returnD =  {'status':'success', 'count':u1Count }
    return returnD

#######

class changeRole_payload(BaseModel):
    usersList: List[str]
    role: str

@app.post("/API/changeRole", tags=["users"])
def changeRole(req: changeRole_payload, x_access_key: Optional[str] = Header(...)):
    cf.logmessage("changeRole api call")
    username, role = authenticate(x_access_key, allowed_roles=['admin'])

    global rolesList
    if req.role not in rolesList:
        cf.logmessage("Invalid role")
        raise HTTPException(status_code=400, detail="Invalid role")
    
    usersListSQL = cf.quoteNcomma(req.usersList)

    u1 = f"""update users
    set role = '{req.role}'
    where username in ({usersListSQL})
    """
    u1Count = dbconnect.execSQL(u1)

    returnD =  {'status':'success', 'count':u1Count }
    return returnD

#####

@app.get("/API/getRoles", tags=["users"])
def getRoles(x_access_key: Optional[str] = Header(...)):
    cf.logmessage("getRoles api call")
    username, role = authenticate(x_access_key, allowed_roles=['admin'])

    global rolesList
    returnD = {'status':'success', 'roles': rolesList}
    return returnD

##############


class deleteUsers_payload(BaseModel):
    usersList: List[str]

@app.post("/API/deleteUsers", tags=["users"])
def listUsers(req: deleteUsers_payload, x_access_key: Optional[str] = Header(...)):
    cf.logmessage("deleteUsers api call")
    username, role = authenticate(x_access_key, allowed_roles=['admin'])

    # validations
    usersList1 = [x for x in req.usersList if x not in (username, 'nikhil_admin','admin1')]

    if not len(usersList1):
        raise HTTPException(status_code=400, detail="No applicable users to delete")

    usersListSQL1 = cf.quoteNcomma(usersList1)
    
    # first fetch the users data
    s1 = f"""select username, email, role, `status`, fullname 
    from users
    where username in ({usersListSQL1})
    and `status` != 'APPROVED'
    order by username
    """
    df1 = dbconnect.makeQuery(s1, output='df')

    if not len(df1):
        cf.logmessage("No non-APPROVED users to delete")
        raise HTTPException(status_code=400, detail="No non-APPROVED users to delete")
    
    usersList2 = df1['username'].tolist()
    usersListSQL2 = cf.quoteNcomma(usersList2)

    d1 = f"""delete from users
    where username in ({usersListSQL2})
    """
    d1Count = dbconnect.execSQL(d1)

    returnD =  {'status':'success', 'count':d1Count }
    return returnD
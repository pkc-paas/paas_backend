# api_users.py

from typing import Optional, List
from pydantic import BaseModel
from fastapi.responses import FileResponse
from Cryptodome.PublicKey import RSA
from fastapi import HTTPException, Header
import secrets, bcrypt

from paas_launch import app
import commonfuncs as cf
import dbconnect


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
        raise HTTPException(status_code=400, detail="Invalid login")
    if len(allowed_roles):
        if user.get('role') not in allowed_roles:
            cf.logmessage(f"Insufficient privileges")
            raise HTTPException(status_code=400, detail="Insufficient privileges")
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
def login(r: loginRBody):
    cf.logmessage(f"login POST api call")
    s1 = f"select username, pwd from users where username='{r.username}'"
    row = dbconnect.makeQuery(s1, output='oneJson')
    if not row:
        raise HTTPException(status_code=400, detail="Invalid username")
    
    if not decrypt(row['pwd'], r.pw):
        cf.logmessage(f"rejected")
        raise HTTPException(status_code=400, detail="Invalid login")
    
    # default else    
    cf.logmessage(f"user {row['username']} authenticated")
    token = secrets.token_urlsafe(25)
    i1 = f"""insert into sessions (token, username, created_on) values 
    ('{token}','{row['username']}', CURRENT_TIMESTAMP)
    """
    iCount = dbconnect.execSQL(i1)
    
    # u1 = f"""update users 
    # set token = '{token}', 
    # last_login = CURRENT_TIMESTAMP
    # where username = '{r.username}'
    # """

    returnD = {
        "message": "Successfully logged in user",
        'token': token
    }

    return returnD    

########################

class changePwBody(BaseModel):
    username: str
    oldpw: str
    newpw: str

@app.post("/API/changepw", tags=["users"])
def changepw(r: changePwBody):
    cf.logmessage(f"changepw POST api call")
    s1 = f"select * from users where username='{r.username}'"
    row = dbconnect.makeQuery(s1, output='oneJson')
    if not row:
        raise HTTPException(status_code=400, detail="Invalid username")
    
    if not decrypt(row['pwd'], r.oldpw):
        cf.logmessage(f"rejected")
        raise HTTPException(status_code=400, detail="Invalid login")

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
    
    # u1 = f"""update users
    # set token=null
    # where token='{x_access_key}'
    # """
    # uCount = dbconnect.execSQL(u1)
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
def createUser(req: createUser_payload, x_access_key: Optional[str] = Header(None)):
    cf.logmessage("createUser api call")

    username, role = authenticate(x_access_key, allowed_roles=['admin'])
    
    s1 = f"select username from users where username = '{req.username}'"
    exist = dbconnect.makeQuery(s1, output="oneValue")
    if exist:
        raise HTTPException(status_code=400, detail="This username is already taken")
        
    hash_string = encrypt(req.pwd)
    i1 = f"""insert into users (username, email, role, pwd, fullname, created_by, created_on) values
    ('{req.username}','{req.email}','{req.role}','{hash_string}','{req.username}','{username}',CURRENT_TIMESTAMP)
    """
    cf.logmessage(f"Creating user {req.username} {req.role} {req.email}")
    iCount = dbconnect.execSQL(i1, noprint=True)
    
    # to do: send automated emails

    returnD = {'status':'success'}
    if iCount:
        returnD['added_count'] = iCount
        return returnD
    else:
        raise HTTPException(status_code=400, detail="Failed to insert new user entry")


########################


class deleteUsers_payload(BaseModel):
    usersList: List[str]

@app.post("/API/deleteUsers", tags=["users"])
def deleteUsers(req: deleteUsers_payload, x_access_key: Optional[str] = Header(None)):
    cf.logmessage("deleteUsers api call")
    username, role = authenticate(x_access_key, allowed_roles=['admin'])
    
    usersListSQL = cf.quoteNcomma(req.usersList)
    d1 = f"delete from users where username in ({usersListSQL})"
    d1Count = dbconnect.execSQL(d1)

    returnD = {'status':'success'}
    returnD['deleted_count'] = d1Count
    return returnD


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

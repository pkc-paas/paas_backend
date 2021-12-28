# api_users.py

from typing import Optional
from pydantic import BaseModel
from fastapi.responses import FileResponse
from Cryptodome.PublicKey import RSA
from fastapi import HTTPException, Header
import secrets

from paas_launch import app
import commonfuncs as cf
import dbconnect

def encrypt(password):
    key = RSA.generate(2048)
    encrypted_key = key.exportKey(passphrase=password, pkcs=8, protection="scryptAndAES128-CBC").decode('utf')
    return encrypted_key


def decrypt(encoded_key,password):
    # from https://stackoverflow.com/questions/2490334/simple-way-to-encode-a-string-according-to-a-password
    if len(password) == 0:
        return False
    try:
        key = RSA.import_key(encoded_key, passphrase=password)
        return True
    except ValueError:
        return False


def authenticate(token, allowed_roles=['admin']):
    s1 = f"select username, role from users where token='{token}'"
    user = dbconnect.makeQuery(s1, output='oneJson', printit=False)
    if not user:
        cf.logmessage(f"rejected")
        raise HTTPException(status_code=400, detail="Invalid login")
    if len(allowed_roles):
        if user.get('role') not in allowed_roles:
            cf.logmessage(f"Insufficient privileges")
            raise HTTPException(status_code=400, detail="Insufficient privileges")
    return user['username'], user['role']


########################

class loginRBody(BaseModel):
    username: str
    pw: str


@app.post("/login")
def login(r: loginRBody):
    cf.logmessage(f"login POST api call")
    s1 = f"select * from users where username='{r.username}'"
    row = dbconnect.makeQuery(s1, output='oneJson')
    if not row:
        raise HTTPException(status_code=400, detail="Invalid username")
    if not decrypt(row['pwd'], r.pw):
        cf.logmessage(f"rejected")
        raise HTTPException(status_code=400, detail="Invalid login")
    
    # default else    
    cf.logmessage(f"user {row['username']} authenticated")
    token = secrets.token_urlsafe(75) # produces a 100 char length string
    u1 = f"""update users 
    set token = '{token}', 
    last_login = CURRENT_TIMESTAMP
    where username = '{r.username}'
    """

    dbconnect.execSQL(u1)

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

@app.post("/changepw")
def changepw(r: changePwBody, x_access_key: Optional[str] = Header(None)):
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
    set pwd = '{new_password}',
    token = null
    where username='{r.username}'
    """
    status = dbconnect.execSQL(u1)

    returnD = {
        "message": "password changed successfully. Pls login with new password."
    }
    return returnD


########################

@app.get("/logout")
def logout(x_access_key: Optional[str] = Header(None)):
    cf.logmessage("logout api call")
    print(x_access_key)
    u1 = f"""update users
    set token=null
    where token='{x_access_key}'
    """
    uCount = dbconnect.execSQL(u1)
    if not uCount:
        cf.logmessage("db error when logging out, but telling frontend to logout out anyways")
    
    returnD = {"message":"Logged out"}
    return returnD

########################

@app.get("/checkUser")
def logout(x_access_key: Optional[str] = Header(None)):
    cf.logmessage("checkUser api call")
    try:
        username, role = authenticate(x_access_key, allowed_roles=[])
    except:
        username, role = None, None
    returnD = {"message":"", "username":username, "role":role }
    return returnD
# api_users.py

from typing import Optional
from pydantic import BaseModel
from fastapi.responses import FileResponse
from Cryptodome.PublicKey import RSA
from fastapi import HTTPException
import secrets

from paas_launch import app
import dbconnect

def encrypt(password):
    key = RSA.generate(2048)
    encrypted_key = key.exportKey(passphrase=password, pkcs=8, protection="scryptAndAES128-CBC")
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


class loginRBody(BaseModel):
    username: str
    pw: str


@app.post("/login")
def getData1(r: loginRBody):
    s1 = f"select * from users where username='{r['username']}'"
    row = dbconnect.makeQuery(s1, output='oneJson')
    if not row:
        raise HTTPException(status_code=400, detail="Invalid username")
    if not decrypt(row['pwd'], r['pw']):
        print(f"rejected")
        raise HTTPException(status_code=400, detail="Invalid login")
    
    # default else    
    print(f"user {row['username']} authenticated")
    token = secrets.token_urlsafe(128)
    timestamp = datetime.datetime.utcnow().replace(microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
    u1 = f"update users set token='{token}'"
    returnD = {
        'token': token
    }

    return returnD    


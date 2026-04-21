import requests
import json

session = requests.Session()
# just a basic check if hitting the view with missing session gets 400
resp = session.post("http://127.0.0.1:8000/auth/ajax-verify-signup-otp/", data={"code": "123456"})
print("Status:", resp.status_code)
print("Text:", resp.text)

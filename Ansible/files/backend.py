from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Mapping
from urllib.parse import urlencode
import requests
import socket
import json

app = FastAPI(openapi_url=None)

# Configuration for Asterisk ARI for when we actually do it
# ARI_URL = "http://127.0.0.1:8088/ari" # or something
# ARI_AUTH = ("asterisk", "your-ari-password") # one-liner to load from /run/{somewhere}

try:
 with open("/run/www-data/secret/csc-placeholder.json", "r", encoding="utf-8") as f:
  csc_placeholder = json.load(f)
except Exception as e:
 csc_placeholder = {}
 print(f"Failed to load secrets: {e}")

class VerificationRequest(BaseModel):
 callsign: str
 password: str

# --------------------------------------------------

@app.post("/h5t/api/verify")
async def verify_identity(payload: VerificationRequest):
# Mocking the future OID4VC verifier flow
 print(f"verify_identity()")
 if payload.callsign.upper() not in { "X1CSC" }:
  raise HTTPException(status_code=403, detail="Identity verification failed")
        
 if payload.password != csc_placeholder.get("password"):
  raise HTTPException(status_code=403, detail="Placeholder verification failed")

# In a full project, your Python script would use the ARI client here 
# to register dynamic PJSIP endpoints or manage the channel setup.
 return {
  "status": "verified",
  "identity": payload.callsign.upper(),
  "wss_url": f"wss://{socket.getfqdn()}/h5t/ws",
  "sip_uri": f"sip:{payload.callsign.upper()}@{socket.getfqdn()}"
 }

# --------------------------------------------------

from fastapi import FastAPI, Form, Response
from typing import Optional

def encode_realtime_payload(payload: Mapping[str, Any]) -> str:
 """Encode Asterisk realtime fields as URL-escaped key=value pairs."""
 return urlencode(payload)

def validate_oid4vc_token():
 return True

@app.post("/h5t/api/pjsip/endpoint/single")
async def pjsip_realtime_endpoint(
 id: Optional[str] = Form(None),
 headers: Optional[str] = Form(None) # Asterisk passes the raw SIP header blob here
):
 print(f"pjsip_realtime_endpoint({id}, {headers})")

 if not id:
  return Response(status_code=200)

 call_sign = id.split("@")[0]


 if call_sign not in ["X1CSC"]:
  return Response(status_code=200)

# Return the full WebRTC behavioral profile dynamically into RAM
# Parse the custom header out of the Asterisk query payload
## if headers and "Authorization: Bearer" in headers:
# Extract the string after "Bearer "
##  token = headers.split("Bearer ")[1].split("\r\n")[0]
# ---> CRYPTOGRAPHIC VALIDATION POINT <---
# Your Python code validates the OID4VC JWT/Token here natively.
# If the token signature is valid and authenticates :
##  if validate_oid4vc_token(token, expected_user=id):
# Bypass the MD5 challenge completely by telling Asterisk 
# this endpoint is pre-authorized (No auth block required)
 payload = {
  "id": id,
  "type": "endpoint",
  "context": "from-webrtc",
  "allow": "ulaw", # TODO restore Opus when a F/OSS codec is available on Debian 13
  "auth": f"auth_{call_sign}",
  "webrtc": "yes",
  "use_avpf": "yes", # WebRTC audio feedback profiles
  "rtcp_mux": "yes", # Multiplex RTCP over the audio port
  # "ice_support": "yes",
  "media_encryption": "dtls",
  "dtls_verify": "no",
  "dtls_setup": "actpass",
  "dtls_auto_generate_cert": "yes",
  # "asymmetric_rtp_codec": "yes",
  "media_use_received_transport": "yes", # Lock media to the proxy interface
  "rtp_symmetric": "yes",
  "force_rport": "yes",
  # "rewrite_contact": "yes",
  "direct_media": "no",
  "rtp_keepalive": "1",
  # "media_address": "13.250.78.226", # TODO this is csc-dev
  # "timers": "no",
  # "send_connected_line": "no",
  "timers": "required", # Asterisk drives the session clock
  "timers_min_se": "90",
  "send_connected_line": "yes", # Allow node telemetry messages
 }
 print (f"returning")
 return Response(content=encode_realtime_payload(payload), media_type="text/plain")

# --------------------------------------------------

@app.post("/h5t/api/pjsip/auth/single")
async def pjsip_realtime_auth(id: Optional[str] = Form(None)):
    print(f"pjsip_realtime_auth()")
    call_sign = id.split("auth_")[1]
    print(f"call sign [{call_sign}]")
    # Asterisk is checking if this auth object profile exists
    # Verify against your runtime validation logic (or mock setup)
    if call_sign not in ["X1CSC"]:
        return Response(status_code=200) # Empty response means "Not Found"

    # Return flat key-value pairs required by res_config_curl
    # Asterisk requires plaintext secrets to verify MD5 challenges over the wire
    payload = {
        "id": id,
        "auth_type": "md5",
        "username": call_sign,
        "password": csc_placeholder.get('password'),
    }
    return Response(content=encode_realtime_payload(payload), media_type="text/plain")

# --------------------------------------------------

if __name__ == "__main__":
 import uvicorn
 uvicorn.run(app, host="127.0.0.1", port=8000)


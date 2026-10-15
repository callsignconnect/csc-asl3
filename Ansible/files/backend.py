from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any
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
 payload = (
  f"id={id}&"
  "type=endpoint&"
  "context=from-webrtc&"
  "allow=ulaw&" #TODO work out how to get Opus support back ; requires a F/OSS codec that Debian 13 is missing
  f"auth=auth_{call_sign}&"
  "webrtc=yes&"
  "use_avpf=yes&"              # Mandated for WebRTC audio feedback profiles
  "rtcp_mux=yes&"              # Multiplexes RTCP over the single audio port
#  "ice_support=yes&"           # Activates WebRTC firewall hole punching mechanics
  "media_encryption=dtls&"
  "dtls_verify=no&"
  "dtls_setup=actpass"
  "dtls_auto_generate_cert=yes&"
# ---- CRITICAL MISSING LINK FOR WEB_RTC CURL LOOKUPS ----
 # "asymmetric_rtp_codec=yes&"   # Instructs Asterisk to allow independent asymmetrical media paths
  "media_use_received_transport=yes" # Locks Asterisk media engine to the proxy interface
  "rtp_symmetric=yes&"          # Enforce symmetric media routing
  "force_rport=yes&"             # Enforce remote port alignment
#  "rewrite_contact=yes&"
  "direct_media=no&"
  "rtp_keepalive=1&"
    # ---- FORCE PURE SYMMETRIC COMEDIA ROUTING OVER ICE ----
   #   "media_address=13.250.78.226&" # TODO This is csc-dev
    # ---- THE CRITICAL ICE ENFORCEMENT PARAMETER FOR DUAL-NAT ----
    # This translates the private candidate into your public EIP on the fly
#            "timers=no&"                  # Force disables Asterisk session timer tracking
#        "send_connected_line=no"      # Prevents out-of-band message flood
        # ---- HEAL 408 TIMEOUT BY ENFORCING SERVER-SIDE KEEPALIVE ----
        "timers=required&"             # Instructs Asterisk to drive the session clock
        "timers_min_se=90&"            # Sets the minimum baseline interval
        "send_connected_line=yes"      # Allows node telemetry messages to flow

 )
 print (f"returning")
 return Response(content=payload, media_type="text/plain")

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
    payload = (
        f"id={id}&"
        "auth_type=md5&"
        f"username={call_sign}&"
        f"password={csc_placeholder.get('password')}"
    )
    return Response(content=payload, media_type="text/plain")

# --------------------------------------------------

if __name__ == "__main__":
 import uvicorn
 uvicorn.run(app, host="127.0.0.1", port=8000)


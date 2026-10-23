# Draft: Call Sign Connect credential profile and SIP guest authorization

Status: discussion draft 0.3. This document specifies intended behavior; it does
not describe functionality already implemented by the prototype. Accepted
decisions are stated explicitly. Remaining format choices, configuration-key
names, and illustrative examples are subject to review.

## 1. Scope and decisions

The demonstration admits authenticated guests to SIP calls to local ASL3 nodes.
It uses SD-JWT VC as its sole credential format and walt.id Verifier API 2 for
OpenID4VP presentation verification. The verifier, authorization backend, and
ASL3 run on one host. Internal verification results and authorization decisions
travel over protected localhost interfaces, not through browser-supplied claims.

The browser is the SIP user agent. It receives an opaque access token and uses
it for RFC 8898 authentication. SIP registration, incoming calls to the browser,
general SIP proxying, and a general-purpose OIDC Provider are out of scope.
Internet node linking remains an ASL3/mod_rpt function, not SIP forwarding.

There are no persistent guest accounts or server-side visitor records outside
logs. Pending presentations, active sessions, SIP tokens, and call context live
in memory. One successful wallet presentation can authorize several calls. A
sealed authorization ticket in a persistent Secure/HttpOnly browser cookie
allows resumption without another presentation or a server-side visitor
database; browser key binding through IndexedDB is deferred. Trust
configuration, service keys, application configuration, and public trust/status
snapshots are persistent deployment data, not guest account records.

The illustrative active-session lifetime is 86,400 seconds. Its expiry prevents
new calls using that session; it does not terminate an already admitted call.
Established calls are not time-limited or actively terminated by authorization
expiry in this iteration. Remembered authorization, active sessions, and
established calls therefore have distinct lifecycles (section 6).

## 2. Meaning of the credential

The subject of the attestation is the holder's right to assert a particular
call sign for a specified period. It is not possession of an individual radio
licence. The model accommodates individual assignments, class-licence regimes,
club call signs, and delegated authority without requiring a personal licence.

The issuer makes an evidence-based assertion under the identified version of
its Certification Practice Statement (CPS). Issuance means that an enrolment
officer followed that procedure and verified the evidence it requires. It does
not itself grant permission to emit radio signals, replace an administration's
authority, or guarantee that the holder has a particular legal entitlement or
set of operating privileges in every context.

The credential type must express this meaning consistently. A Call Sign Connect
attestation must not be presented as though it were a licence issued by an
administration. The CPS defines the evidence and assurance behind the assertion,
including the procedures for club or delegated call signs. Raw document images,
biometric data, and an enrolment officer's personal details are not required in
the credential presented to this service.

## 3. Proposed credential profile

### 3.1 Type, issuer, time, and holder binding

Use the selected SD-JWT VC specification's standard metadata and presentation
machinery rather than parallel application-specific equivalents.

| Item | Requirement and meaning |
| --- | --- |
| `vct` | Required exact value `tag:callsignconnect.cloud,2026-10:call-sign-attestation:1`. |
| `iss` | Required issuer identifier. An identifier or name alone never establishes trust. |
| `iat` | Required issuance time. It does not replace the assertion's validity interval. |
| `nbf`, `exp` | Required start and end of the time interval for which the issuer attests the holder's right to assert the call sign. Accept only while `nbf <= now < exp`, subject to a small configured clock tolerance. |
| `cnf` | Required binding to the holder's public key, as specified by the chosen SD-JWT VC profile. |
| Credential status reference | Required means of checking revocation or suspension against locally cached status material. Its exact wire representation remains to be selected. |

The CPS must ensure that the issued interval does not exceed the interval
supported by the evidence or delegation. These dates do not imply that a
personal licence exists. Separate source-document validity dates should be
added only if they convey a distinct fact the application needs.

Presentation must prove possession of the bound holder key. Verify the
key-binding JWT, including its relationship to `cnf`, the intended verifier
audience, a fresh single-use nonce, suitable issuance time, and `sd_hash`.
A valid issuer signature without a valid holder-bound presentation is
insufficient. A completed presentation must also be bound to the browser's
original login transaction; knowing a presentation session identifier must not
let another browser claim its result. Section 6.1 specifies a browser-bound
transaction using an independent secret cookie and a server-side association
with the verifier session. Wallet nonce/key binding and browser binding solve
different parts of the flow; neither replaces the other.

The selected type identifier is
`tag:callsignconnect.cloud,2026-10:call-sign-attestation:1`. The name
describes an attestation about a call sign without implying an administration
issued a radio licence. The final `:1` denotes a schema/semantics version; the
tag's `2026-10`
date identifies the domain-control namespace and is not a credential issuance
date or expiry date. Use of that namespace assumes the
project controlled `callsignconnect.cloud` at the specified time.

SD-JWT VC does not require an HTTPS `vct`. A tag URI has no automatic HTTPS
retrieval location. At issuance, the issuer supplies type metadata directly to
the wallet; the delivery mechanism is deferred until issuer integration. At
verification, the integration supplies a local copy directly to walt.id through
its supported metadata mechanism. Correct operation does not depend on a prior
or login-time remote fetch. Check wallet and walt.id support for those delivery
mechanisms. As a naming
comparison, the EUDI PID issuer uses `urn:eudi:pid:1` for Person Identification
Data; the type describes the attested subject matter rather than using the
generic word `credential` or `certificate`.

Pin the accepted SD-JWT VC and OpenID4VP versions, key-binding requirements,
and permitted cryptographic algorithms in the deployment profile. Select a
supported walt.id release and verify those capabilities before implementation;
the choice of product does not establish that its defaults meet this document.

### 3.2 Application claims

The application claims for this iteration are `call_sign` and `cps`. Both are
covered by the issuer signature and must be disclosed during presentation.

| Proposed claim | Meaning |
| --- | --- |
| `call_sign` | One canonical call sign that the holder is entitled to assert under this attestation. It is the basis of the SIP identity and local list matching. |
| `cps` | Required object containing an immutable, version-specific `uri`. An optional `sha256` binds the exact CPS document bytes. |

`call_sign` must use uppercase ASCII letters and digits and satisfy the call
sign formation rules in ITU Radio Regulations Nos. 19.68, 19.68.1, 19.68A, and
19.69. The formal validator must implement those provisions, including their
exceptions; a simplified guessed regular expression is not the specification.
Reject malformed or noncanonical signed values rather than silently fixing
them. Local list entries use the same canonical representation.

Do not constrain syntax validation by the prefix allocations in Appendix 42.
An issuer's authority to certify a prefix is determined by the configured
project trust list and its attached delegation material (section 4). This
separates syntactic validity from permission to assert a particular prefix.
Use `X1CSC` or other syntactically compliant signs synthesized under the
unallocated `X1` prefix for examples. Staging/test configurations can authorize
only such prefixes and exclude allocated real-world prefixes through trust
data, without source-code exceptions. Malformed signs remain invalid even in
staging; an unallocated prefix is a different issue.

Portable prefixes/suffixes, alternative call signs, and operating-location
assertions are outside the profile. These are operating obligations beyond
the assertion the issuer certifies. No such additions are inferred from a
browser-supplied value.

The `vct` versions the claim meanings. The CPS URI versions the enrolment and
evidence procedure. They serve different purposes. A mutable URL such as
`/cps/current` is insufficient as the sole CPS reference. A project issuer's
reference may be `https://callsignconnect.cloud/cp-cps-1.0`. No component needs
the CPS document to complete issuance or verification automatically, so it
need not be proactively delivered or cached. It must not be fetched during
login. The holder/subject may open its URI in a browser to read the procedure.

### 3.3 Illustrative disclosed claims

This is a logical claim-set illustration, not an encoded SD-JWT or an issuable
example. The type identifier is selected; the issuer URL and holder-key
coordinates are placeholders. `X1CSC` is a synthetic example and would require
an appropriate test trust-list delegation. Status metadata is omitted pending
the status-format decision.

```json
{
  "iss": "https://issuer.example.invalid",
  "vct": "tag:callsignconnect.cloud,2026-10:call-sign-attestation:1",
  "iat": 1792540800,
  "nbf": 1792540800,
  "exp": 1824076800,
  "cnf": {
    "jwk": {
      "kty": "EC",
      "crv": "P-256",
      "x": "<holder-public-key-x>",
      "y": "<holder-public-key-y>"
    }
  },
  "call_sign": "X1CSC",
  "cps": {
    "uri": "https://callsignconnect.cloud/cp-cps-1.0"
  }
}
```

### 3.4 Deferred attributes and use cases

`country`, `licence_class`, administration-document vocabularies, equivalence
mappings, restrictions, extensions, and endorsements are outside this
iteration. Their omission does not imply unrestricted legal operating rights.
Remote control of an HF transmitter is a separate use case requiring further
assurance information and policy, potentially along the IAL/AAL/FAL dimensions
of NIST SP 800-63. Enrolment through an EchoLink or RadioID bridge must not be
assumed sufficient for that use case. None of those future features is needed
for the current ASL3 demonstration.

## 4. Cryptographic trust and offline status checking

Accept credentials only when the verified credential-signing key is authorized
by locally cached project trust material. Two trust paths are supported in the
design:

1. A valid certification path from a locally pinned project trustee to an
   issuer's credential-signing key.
2. A directly pinned issuer signing key or certificate with an explicitly
   configured administrative delegation.

Check signature validity, certificate/key usage, applicable validity and
revocation, and delegation scope. In particular, the trust list specifies the
call-sign prefixes the issuer may certify. Credential types, CPS versions, or
administrative roles may also be constrained. Match the verified `call_sign`
against that issuer/key's permitted prefix scope. The syntax validator does not
contain the global prefix-allocation table. Production and staging/test trust
lists can therefore admit disjoint prefix sets through data alone. Issuer
names, certificate subject names, `kid`, and remotely discovered keys are not
independent trust anchors.

The backend must have a trustworthy link between the verified credential and
the signing-key/trust-path result. Neither an issuer-name match nor a
browser-supplied `verified` flag is an adequate substitute. Determine whether
the required policy is best implemented inside a supported walt.id verification
policy interface or through an authenticated server-side result containing
sufficient verification evidence.

The trust list and attached material include everything needed to identify
trusted issuers and validate their signing authority. Supply type metadata
locally as described in section 3.1. A provisioned set must allow correct
operation without first fetching remote metadata or other referenced objects.

Attempt an automatic refresh of the trust list, public trust material, and
revocation/status artifacts every 24 hours. Authenticate downloads using pinned
project/issuer signing authority as appropriate, preserve TLS verification,
validate artifact signatures and versions, and apply the freshness policy below.
Install a verified snapshot atomically and prevent rollback to an older accepted
version. An incomplete or failed refresh must not reset the successful-refresh
time of the required set.

Distinguish these objects even if one distribution mechanism carries them:

- Removal or limitation of an issuer's project delegation.
- Revocation of an issuer signing certificate/key, including any applicable
  X.509 certificate revocation list (CRL).
- Revocation or suspension of an individual credential, potentially represented
  by a signed bitstring status list.

The last item is not automatically the same format or object as an X.509 CRL.
Choose the credential-status representation and its SD-JWT reference before
finalizing the wire profile. Pin or authenticate the status-list signer's
authority; a status URL in a credential does not authorize arbitrary content.

All login, resumption, and new-call validation uses the locally supplied
snapshot. Do not fetch issuer metadata, keys, trust chains, type metadata, CRLs,
or credential status on demand. Unknown keys, prefixes, or status references
are rejected without a network fallback. This rule also covers automatic
library fetches such as certificate AIA/OCSP resolution and JOSE key URLs.
A wallet-supplied URL is not a refresh instruction. The CPS document is a
human-readable reference, not a verification input, and requires no automatic
delivery or fetch at any stage.

Two cache-acceptance modes are specified:

| Mode | Acceptance and failure behavior |
| --- | --- |
| Normal (default) | Maximum cache age is 73 hours since the last successful authenticated refresh of the required snapshot. Reuse the snapshot during refresh failures within that window; after it, reject new authorizations, resumptions, and calls until a successful refresh. This allows two consecutive missed 24-hour refresh attempts. |
| Manual indefinite holdover | An administrator deliberately selects the last verified snapshot for offline operation. Treat that snapshot as authoritative without an age cutoff for the duration of the selected mode. Do not enter this mode automatically after refresh failure. |

Holdover is intended for planned Field Day, EmComm, and beyond-grid operation.
It accepts the risk of revocations or trust changes not learned after the held
snapshot. It does not undo revocations already present in that snapshot, accept
invalid signatures, expand an issuer's prefix authority, waive holder binding,
or extend a credential's own `nbf`/`exp` interval. Normal certificate/key and
delegation validity checks also remain separate from cache freshness. Log the
administrator's holdover selection and when normal operation resumes, and make
the active mode visible to the administrator.

Cached-artifact publication freshness deadlines, such as CRL `nextUpdate`, are
handled under the selected cache policy, including the explicit holdover
override. They must not silently impose a shorter refresh-failure window than
the configured policy. This is distinct from extending the underlying call
sign assertion or an issuer/delegation's own validity. Missing or unverifiable
required material is not repaired by either mode.

With normal operation, the local revocation-detection delay can be up to 73
hours during refresh failures, assuming promptly published updates. Manual
holdover has no bounded revocation-detection delay. Neither mode causes an
established call to be terminated automatically.

## 5. Initial local authorization policy

### 5.1 Admission

Admit a guest when all of the following hold:

1. The presentation meets the accepted credential profile, holder-binding,
   cryptographic trust, time, and cached status requirements above.
2. It contains one unambiguous canonical call sign.
3. Its call sign is within the issuer/key's prefix delegation.
4. That call sign is not on the configured access block list.

Permit admitted guests to call any configured local node. Reject nonlocal
destinations. There is no initial per-node guest
eligibility mapping. Access denial overrides every Rpt mode setting.

### 5.2 Rpt control mode

Represent the effective per-call privilege using the same one-letter mode
passed to `Rpt()`:

| `rpt_mode` | Intended behavior |
| --- | --- |
| `P` | Phone Control: full access to commands exposed by the node's `phone_functions` table, including its PTT command. |
| `S` | Simplex Dumb Phone Control: PTT control without the other phone command functions. |

The initial profile permits only `P` and `S`. This is not a policy to discard
all DTMF: mode `S` deliberately retains PTT control. Under default app_rpt
settings, `P` uses the configured command `*99` to key/toggle PTT, while `S`
uses the function character `*`; `#` unkeys in both cases. Actual command maps
and function/end characters are node configuration. The browser's PTT sequence
must match the selected mode and configured node, and must be tested against
the deployed app_rpt version. Modes have their documented audio/control
semantics as well as a different command set; do not assume they are otherwise
interchangeable.

Translate the earlier DTMF allow/block policy into permission for full phone
control. Proposed precedence is explicit full-control deny first, then the
default/allow rule:

```text
if not admitted:
    deny call
elif call_sign in full_control_blocklist:
    rpt_mode = "S"
elif rpt_mode_default == "P":
    rpt_mode = "P"
else:
    rpt_mode = "P" if call_sign in full_control_allowlist else "S"
```

Default `P` therefore gives full control except to call signs on the
full-control block list, which receive `S`. Default `S` gives full control only
to allowlisted call signs not also blocked. The block-list-wins rule resolves
accidental membership in both lists. Lists use the same canonical call-sign
matching as admission; patterns and wildcards are out of scope.

Illustrative configuration, not an implemented configuration file:

```yaml
authorization:
  access_blocklist: []
  rpt_mode_default: P       # P or S
  full_control_blocklist: []
  full_control_allowlist: [] # used when rpt_mode_default is S
  session_lifetime_seconds: 86400
trust_cache:
  refresh_interval_seconds: 86400
  max_cache_age_seconds: 262800  # 73 hours in normal mode
  mode: normal                 # normal or manual_holdover
```

List and mode changes apply to newly established calls, including calls made
with an unexpired token issued before the configuration change. Recompute the
access decision and Rpt mode at each new call using the current local policy.
In this iteration, existing calls retain their mode until they end.
Immediate application of policy or revocation updates to active calls is an
optional extension, not assumed implementation behavior.

Compute `rpt_mode` from authenticated call-sign context on the server and bind
it to the channel before invoking `Rpt()`. Preserve the one-letter value through
the protected backend-to-SIP integration. A browser may receive the mode to
render appropriate controls, but neither a browser-supplied mode nor a forged
SIP header can elevate it. Disabling a keypad button is not enforcement.

Use app_rpt's mode handling to enforce command access, not blanket DTMF-frame
suppression. Confirm that mode `S` permits the intended PTT operation and denies
other node command functions through the relevant input paths. It is not a
promise that audio contains no tones or that a downstream linked system cannot
interpret them. The existing `application/asterisk-features` PTT INFO messages
are not assumed to work independently of the DTMF path.

## 6. Remembered authorization, sessions, and calls

These are distinct lifecycles:

| Object | Location and lifetime |
| --- | --- |
| Pending presentation transaction | Backend/verifier memory and a browser-binding cookie; short-lived and single-use. |
| Sealed authorization/resumption ticket | Persistent Secure/HttpOnly browser cookie; may last up to the underlying call-sign authorization period, subject to browser retention and later freshness-policy decisions. No persistent server-side visitor record. |
| Active session and opaque SIP access token | Backend memory, with the token held in browser memory; illustrative lifetime 86,400 seconds, capped by applicable authorization validity. |
| Established call | Asterisk channel/dialog and necessary backend context; continues until ended, with no authorization-expiry hangup or call-duration limit in this iteration. |

### 6.1 Browser binding and initial presentation

Use an independent browser secret as well as the presentation transaction
identifier. One concrete same-origin flow is:

1. The browser starts a login transaction through a same-origin POST. The
   backend sets an unpredictable, host-only `Secure; HttpOnly; SameSite=Strict`
   transaction cookie, for example `__Host-csc-login` with `Path=/` and no
   Domain, Max-Age, or Expires attribute. Protect state-changing endpoints with
   an Origin check and a session-bound CSRF token; reject cross-origin
   initiation. This temporary cookie is distinct from the persistent ticket.
2. The backend creates the walt.id verification session over localhost. In
   memory it records the public transaction identifier, a digest of the browser
   secret, verifier session identifier, expected nonce/audience, deadline, and
   pending/consumed state. The browser receives request/QR-code data, never the
   independent secret in a URL or QR code.
3. The wallet submits its presentation to the verifier. The backend obtains the
   authenticated outcome directly from the verifier over localhost and links
   it to that transaction. The wallet callback needs no browser cookie and
   does not authorize delivery of a token to the callback's sender.
4. The initiating page polls or completes through the same-origin backend with
   its cookie. Require the correct browser secret, matching completed
   transaction, deadline and appropriate CSRF checks. Evaluate admission and
   atomically consume the transaction. The identifier alone cannot claim the
   result. Completion retries must not create additional authorizations.
5. Rotate transaction/session credentials after successful authentication,
   issue a sealed remembered-authorization ticket, and create an active
   in-memory session and opaque SIP token. Expire the pending record on
   completion, cancellation, or timeout.

Expose only the wallet-facing verifier routes needed by the presentation
protocol. Keep result lookup, session management, and token issuance control
behind the backend/localhost boundary. Keep secrets out of URLs, QR codes, and
logs. Browser binding prevents another browser claiming a completed result; it
does not by itself prevent a person approving an attacker-initiated wallet
request. Wallet identification of the verifier and deliberate approval remain
necessary. Do not assume the wallet remembers a previous disclosure decision.

### 6.2 Remembered authorization and resumption

The sealed ticket records the original authorization facts and deadline, with
only the references needed for later local checks: canonical call sign,
credential type/CPS reference, original credential validity and status
reference, verified issuer signing-key/delegation identity, and intended host.
It is authenticated and encrypted using established cryptographic libraries
and durable host service keys. The browser cannot read or change its contents
successfully. The precise ticket format and key-rotation procedure remain
implementation choices; do not accept arbitrary browser-selected algorithms
or key URLs.

Store the ticket in a persistent, host-only cookie such as
`__Host-csc-authorization`, with `Secure; HttpOnly; SameSite=Strict; Path=/`, no
Domain attribute, and a bounded Max-Age/Expires. Its deadline must not exceed
the underlying attested authorization or applicable delegation validity.
Issuance/freshness rules that may further limit remembered authorization are
explicitly deferred. Browser expiry limits, clearing, or eviction may shorten
retention; no promise of uninterrupted multi-year browser storage is made.

On return, the browser supplies the cookie automatically to the same-origin
backend. The backend authenticates/decrypts it, checks its host and validity,
and applies current local trust/status/prefix and access policy before creating
a new in-memory session. It does not require a fresh wallet presentation just
because an earlier one-day session expired or the backend restarted, provided
the ticket, host keys, and current local validation material remain usable.
A resumed session cannot silently extend the original authorization deadline.
There is no IndexedDB key, device proof, or non-extractable-key requirement in
this iteration.

Only the ticket is retained in the browser persistently. No per-visitor ticket
record is written to the host's persistent storage; service sealing keys and
public trust/status data are deployment configuration. The ticket is a bearer
credential: HttpOnly prevents direct JavaScript reads, not authenticated
requests made by malicious same-origin JavaScript. Clear the cookie when the
user chooses to forget remembered authorization. Clearing one browser copy
cannot revoke a stolen copy; individual ticket revocation beyond credential
status and the configured access block list is not specified here.

### 6.3 Active session and SIP access token

Generate a cryptographically random opaque SIP token with at least 256 bits of
entropy. Keep it only in browser memory, not localStorage, IndexedDB, or a
persistent cookie. It is a random reference to an in-memory session, distinct
from the sealed resumption ticket. The browser may receive its authorized mode
for rendering controls, but browser-supplied attributes never become authority.
Holder binding of the original presentation does not make either bearer
credential non-transferable.

Keep a digest-indexed authorization record in memory:

| Item | Purpose |
| --- | --- |
| Random session identifier and SIP-token digest | Lookup without logging or retaining the raw token as the lookup key. |
| Canonical call sign and permitted SIP identity | Bind SIP identity to verified authorization facts. |
| Intended local SIP service | Prevent use at another service or host. |
| Issue and expiry times | Control eligibility to establish new calls. |
| Issuance-policy and trust/status snapshot versions | Explain admission; each new call also records its current local policy version. |
| Minimal credential/key/status references and normalized policy inputs | Recheck authorization for later calls without retaining the presentation or personal evidence. |

Use a narrow protected localhost interface, or a direct in-process call where
appropriate, for SIP-side token validation and the resulting authorization
context. RFC 7662 introspection is not implemented: the collocated customized
components do not need that interoperable protocol.

The session may authorize multiple calls. Hangup does not consume it. Set the
illustrative `session_lifetime_seconds` to 86,400 and cap expiry by the original
credential/ticket and applicable delegation validity. Check current cache
acceptability at resumption and new-call establishment; do not permanently
shorten a remembered ticket merely because its original public snapshot was
replaced or aged out. A usable ticket can resume a session without another
wallet interaction. If the ticket is missing, invalid, expired, or no longer
authorized, a new presentation may be needed. Missing or unverifiable public
validation material must first be repaired. Material unusable solely because
of cache freshness can instead be placed in explicitly selected manual
holdover.

### 6.4 New call establishment

The SIP user agent sends the access token using RFC 8898 Bearer authentication
on the INVITE, either initially or in response to a challenge. Use only the
preconfigured local authorization server; a challenge cannot redirect the
client to an arbitrary third-party server.

Before admitting a new call, resolve the session through the backend and check
token validity/expiry, the call-sign access block list, the intended SIP
service, the permitted SIP identity, and the configured local destination.
Recheck current locally cached credential status and issuer/key/prefix
permission under the selected cache mode. Compute `rpt_mode` from current local
policy. Newly learned revocation, delegation removal, or unusable required
cache material prevents new calls even with an otherwise unexpired token.

Reject forged SIP identities or caller-controlled fields that conflict with
the grant. A successful PJSIP endpoint lookup alone is not authentication.
Bind trusted identity, session reference, current policy version, and `rpt_mode`
to the actual Asterisk channel/dialog. Browser-supplied headers or variable
names must not elevate privilege. There is no additional concurrent-call limit.

A duplicate belonging to the same SIP transaction must not create another call
or consume another admission. SIP request retransmission is normally needed
for unreliable transports such as UDP when a request/response is lost; it is
not normally used over this browser's reliable WSS transport. An authenticated
INVITE after a 401/407 challenge is a new transaction, not a retransmission;
a re-INVITE is a separate in-dialog transaction. Treat existing-dialog
maintenance and teardown correctly after session expiry, without turning them
into new node access or a privilege elevation. Repeated responses and ACK
handling remain SIP-stack responsibilities.

RFC 8898 section 2.1.2 still applies: select and validate a mechanism ensuring
only authorized SIP endpoints can access the opaque token. Review the
browser/WSS/Apache/Asterisk path, local interfaces, and logging. No general SIP
proxying simplifies the analysis but does not itself prove compliance.

### 6.5 Expiry, established calls, and cleanup

Session/token expiry blocks new call establishment, but does not time-limit or
actively terminate an established call. Do not install an absolute call timeout,
expiry-driven hangup, or background revocation/policy-driven termination in this
iteration. An admitted call may continue indefinitely until ended. Expiry
warnings, asynchronous reauthorization, and mid-call enforcement are deferred.
This intentionally permits a call to outlive the authorization interval used
to admit it; it is a project lifecycle policy, not a property supplied by RFC
8898. The existing call keeps its admitted mode without gaining new privileges.

Remove expired pending transactions and active session/token lookup records.
An established call retains only the identity/mode and other context needed
for its operation and logs until it ends; do not retain the entire presentation
or an unnecessary expired token record solely because that call continues.
Unkey transmission and clean up the node/channel normally when the call ends.

A backend restart loses active sessions and SIP-token lookups, so old random
SIP tokens fail new-call validation. A retained sealed ticket may create a new
session if its host keys and current validation material remain available.
Existing Asterisk calls need not be terminated merely because the backend
restarted. A whole-host restart naturally ends its calls. Log minimal decision,
refresh/holdover, and call-end events, never bearer tokens, sealed tickets,
SD-JWTs, disclosures, private keys, or biometric/document evidence.

## 7. Implementation boundaries to prove

The implementation replaces the placeholder authentication flow with
OpenID4VP presentation, remembered authorization, and subsequent SIP access
authorization. Remove the placeholder-password path rather than retain it as
an alternative admission route. The current prototype still uses that path
and a PJSIP digest password; it does not implement RFC 8898 or this policy.
The browser has `register: false` and the PJSIP wizard disables registration.

The current `from-webrtc` dialplan answers the call and enters `Rpt(...,P,...)`
without a server-selected mode or token admission check. Verify these
integration points before choosing implementation details:

- Browser SIP-stack support for RFC 8898 INVITE authentication.
- An inbound SIP Bearer-authentication/validation path that reaches the backend
  at the right point, before node access; existing realtime lookups alone do not
  establish this capability.
- A trusted way to attach the backend's decision to one channel, without using
  persistent user or per-call files.
- Local type/issuer/trust metadata delivery and the two cache-failure modes,
  with no remote metadata-resolution fallback.
- Sealed-cookie resumption with no persistent server-side visitor record.
- Selection of per-call `P`/`S` mode, command isolation, and the mode-dependent
  PTT sequences, including concurrent callers with different modes.
- Rejection of new calls after token expiry without terminating existing
  calls, including correct existing-dialog behavior and component restarts.

Use the existing `Rpt()` mode argument for command policy. Do not add an
authorization-expiry call timer. Mode behavior, linked-node behavior, PTT,
normal call-end cleanup, and the interaction with `app_rpt` need real tests.

## 8. Acceptance examples

These are future integration-test requirements, not tests already executed.

| Scenario | Expected result |
| --- | --- |
| Valid holder-bound credential and authorized issuer, call sign not blocked | Permit call to a configured local node. |
| Valid club/delegated/class-licence call-sign assertion under the issuer's CPS | Apply the same admission rule; no personal-licence document requirement. |
| Correct issuer name but untrusted signing key, or wrong delegation scope | Reject. |
| Syntactically valid `X1CSC` and issuer explicitly delegated `X1` in staging | Permit if otherwise valid; no source-code exception for `X1`. |
| Syntactically valid allocated prefix outside the staging issuer's delegation | Reject, even if Appendix 42 assigns that prefix in the real world. |
| Malformed or nonuppercase signed `call_sign` | Reject regardless of prefix delegation. |
| Trusted issuer but missing holder proof, wrong audience/nonce, or replayed presentation | Reject. |
| Credential outside its assertion interval, revoked/suspended in the accepted snapshot, or required material unverifiable | Reject without an on-demand issuer/status fetch. |
| Automatic refresh fails twice; authenticated snapshot is 72 hours old in normal mode | Accept the cache within the 73-hour limit, subject to other checks. |
| Snapshot exceeds 73 hours in normal mode | Reject new authorizations, resumptions, and calls; do not enter holdover automatically. |
| Administrator selects manual holdover with a valid previously verified snapshot | Continue using that snapshot regardless of cache age, retaining its known revocations and other non-freshness checks. |
| Valid credential with blocked call sign | Reject regardless of full-control lists. |
| Default `P`; call sign not full-control-blocked | Permit call in mode `P`. |
| Default `P`; call sign full-control-blocked | Permit call in mode `S`, retaining PTT but not other phone commands. |
| Default `S`; call sign allowlisted and not blocked | Permit call in mode `P`. |
| Default `S`; call sign absent from allow list, or present in both lists | Permit call in mode `S`. |
| Browser changes claimed identity, target to a nonlocal node, or `rpt_mode` | Reject conflicting identity/destination; never accept a browser-supplied mode as authority. |
| Another browser knows a completed presentation's transaction identifier but lacks the bound cookie | Refuse completion and token delivery. |
| Initiating browser makes a second call within its valid guest session | No new wallet presentation; recheck current local policy and select the new call's mode. |
| Active session is lost/expired but browser retains a valid sealed ticket | Resume through current local validation without another wallet presentation. |
| Session/token expires during an established call | Let the call continue; reject new calls using that expired token. |
| Policy changes after token issuance but before a new call | Apply the current access/full-control lists when establishing that new call. |
| A daily refresh revokes the credential or issuer after token issuance | Reject subsequent calls/resumptions; do not actively terminate already admitted calls. |
| Repeated INVITE belongs to the same SIP transaction | Do not create another call or consume another admission. |
| Verifier observes an unknown signing key or status reference | Reject using local data only; schedule any investigation/refresh separately. |

## 9. Decisions remaining before implementation

1. Finalize CPS identifiers and the status-reference claim shape. The `vct` is
   selected; additional attributes, licence-class vocabularies, and remote-HF
   assurance policy are deferred.
2. Pin the SD-JWT VC/OpenID4VP release profile, derive the call-sign syntax
   validator from the cited Radio Regulations provisions, and select the
   credential-status representation, including suspension semantics.
3. Specify the signed trust-list/delegation format and prefix-scope encoding,
   issuer certification rules, local metadata interfaces, and complete snapshot
   refresh/holdover mechanics. The refresh interval and default maximum age
   are selected, not open configuration-policy questions.
4. Select the sealed-ticket format/key lifecycle and remembered-authorization
   freshness rules. The active-session example is one day; established-call
   expiry enforcement and warning/reauthorization UX are deferred.
5. Prove browser binding/resumption, SIP Bearer admission, per-call mode/PTT,
   and cleanup without expiry-driven call termination.

## References

- [RFC 8898: Third-Party Token-Based Authentication and Authorization for SIP](https://www.rfc-editor.org/rfc/rfc8898.html), particularly sections 2.1.2 and 3.
- [ITU Radio Regulations, 2024 edition](https://www.itu.int/pub/R-REG-RR-2024), Nos. 19.68, 19.68.1, 19.68A, and 19.69; Appendix 42 allocation checks are not part of this profile's syntax validator.
- [RFC 3261 SIP INVITE transaction processing](https://www.rfc-editor.org/rfc/rfc3261.html#section-17.1.1.1) and [authentication retry behavior](https://www.rfc-editor.org/rfc/rfc3261.html#section-22.2).
- [RFC 7118: SIP over WebSocket](https://www.rfc-editor.org/rfc/rfc7118.html).
- [SD-JWT-based Verifiable Credentials](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/).
- [SD-JWT VC type identifiers and metadata](https://github.com/oauth-wg/oauth-sd-jwt-vc/blob/main/draft-ietf-oauth-sd-jwt-vc.md).
- [RFC 4151: The tag URI Scheme](https://www.rfc-editor.org/rfc/rfc4151.html).
- [EUDI reference issuer PID type metadata](https://github.com/eu-digital-identity-wallet/eudi-srv-pid-issuer/blob/main/src/main/resources/vct/pid_v1.4.json).
- [OpenID for Verifiable Presentations 1.0](https://openid.net/specs/openid-4-verifiable-presentations-1_0.html).
- [walt.id Verifier API 2](https://github.com/walt-id/waltid-identity/tree/main/waltid-services/waltid-verifier-api2).
- [app_rpt mode documentation and implementation](https://github.com/AllStarLink/app_rpt/blob/22b60b5de6a7d99e3042f9b413d129dee3b97ad0/apps/app_rpt.c#L367).

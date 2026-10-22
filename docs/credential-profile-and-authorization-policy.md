# Draft: Call Sign Connect credential profile and SIP guest authorization

Status: discussion draft 0.2. This document specifies proposed behavior; it does
not describe functionality already implemented by the prototype. Claim names,
identifiers, configuration keys, and examples below are proposals for review.

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

There are no persistent guest accounts. Short-lived presentation, token, and
call state live in memory. This is not literal statelessness: one successful
wallet presentation establishes an in-memory guest session that can authorize
several calls until it expires. Ending a call does not end that session or
require another wallet interaction for the next call. Trust configuration,
service keys, application
configuration, and cached public trust/status artifacts are deployment data;
they are not guest account records.

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
| `vct` | Required collision-resistant, case-sensitive identifier for this credential's schema and semantics. A tag URI is proposed; the final name and schema-version convention remain to be assigned. |
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

A candidate type identifier is
`tag:callsignconnect.cloud,2026-10:call-sign-attestation:1`. The proposed name
describes an attestation about a call sign without implying an administration
issued a radio licence. `call-sign-assertion` is an alternative to settle during
review. The final `:1` denotes a schema/semantics version; the tag's `2026-10`
date identifies the domain-control namespace and is not a credential issuance
date, expiry date, or vocabulary version. Use of that namespace assumes the
project controlled `callsignconnect.cloud` at the specified time.

SD-JWT VC does not require an HTTPS `vct`. A tag URI has no automatic HTTPS
retrieval location, so distribute its type metadata through explicit issuer/
wallet configuration or an agreed registry and keep the verifier's copy cached.
Check wallet and walt.id support for this metadata arrangement. As a naming
comparison, the EUDI PID issuer uses `urn:eudi:pid:1` for Person Identification
Data; the type describes the attested subject matter rather than using the
generic word `credential` or `certificate`.

Pin the accepted SD-JWT VC and OpenID4VP versions, key-binding requirements,
and permitted cryptographic algorithms in the deployment profile. Select a
supported walt.id release and verify those capabilities before implementation;
the choice of product does not establish that its defaults meet this document.

### 3.2 Application claims

The following claims are covered by the issuer signature. Selective disclosure
may be used, but the service requires disclosure of the call sign, country, and
CPS reference. Licence class may be omitted or withheld because initial
admission does not depend on it. The verifier cannot distinguish an absent
optional claim from one the holder has not disclosed; either case provides no
class assertion to this service. A future policy that depends on class must
require its disclosure explicitly.

| Proposed claim | Meaning |
| --- | --- |
| `call_sign` | One canonical call sign that the holder is entitled to assert under this attestation. It is the basis of the SIP identity and local list matching. |
| `country` | Uppercase ISO 3166-1 alpha-2 code for the jurisdiction relevant to that call-sign assertion. It is not the holder's nationality, current location, or issuer's place of incorporation. |
| `licence_class` | Optional string containing the qualification, licence, or authorization document/category name as used by the issuing administration, in its original language/script. Omit where no category applies; do not invent an `unknown` class. |
| `cps` | Required object containing an immutable, version-specific `uri`. An optional `sha256` binds the exact CPS document bytes. |

The project maintains a recommended vocabulary of administration-native names,
with countries and authoritative sources, independently of this credential
profile. The credential carries the name, not a project code or vocabulary
version. Adding, correcting, or encountering a name does not require a profile
revision or credential reissuance. An unfamiliar class name is a valid value;
initial admission does not filter by country or licence class, and must not
reject a credential merely because a value is absent from the local vocabulary.

Do not replace an administration's name with an English translation unless that
is itself the name the administration uses. The ACMA Amateur Radio
Qualification Framework survey can identify sources to investigate, but its
translated titles are not automatically suitable credential values. The
vocabulary, transliteration/display conventions, and any later
application-specific equivalence mapping are separate work. They need not be
resolved to implement the initial admission rule.

If multiple source categories need to be represented, define their semantics
explicitly before extending this single-category draft. Similar-looking names
do not imply equivalent privileges across countries. Future policy that uses
equivalence mappings must explicitly handle unrecognized names rather than
invent an equivalence.

Use a canonical call sign agreed in the credential profile. For local matching,
trim surrounding whitespace and use ASCII uppercase; reject malformed or
ambiguous values rather than silently rewriting them. Portable prefixes,
suffixes, alternative call signs, and operating-location assertions are not
derived or added by the browser. Their representation needs an explicit future
profile rule. The country/call-sign relationship must not be guessed from a
prefix alone, particularly for territories or delegated arrangements.

The `vct` versions the claim meanings. The CPS URI versions the enrolment and
evidence procedure. They serve different purposes. A mutable URL such as
`/cps/current` is insufficient as the sole CPS reference. CPS material is
distributed and cached with public project material; login must not fetch it.

### 3.3 Illustrative disclosed claims

This is a logical claim-set illustration, not an encoded SD-JWT or an issuable
example. URLs, identifiers, holder keys, and the administration-native name are
placeholders. Status metadata is omitted pending the status-format decision.

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
  "call_sign": "<canonical-call-sign>",
  "country": "AU",
  "licence_class": "<document-or-class-name-used-by-the-administration>",
  "cps": {
    "uri": "https://example.invalid/csc/cps/1.0"
  }
}
```

### 3.4 Restrictions and extensions

Do not include a generic `restrictions` field in the initial profile. A free-text
caveat must not silently contradict machine-readable claims or require an
operator to interpret text before authorization can be safe. Omission of this
field does not imply unrestricted legal operating authority.

Examples that could justify future typed constraints include:

- A delegate may assert a club call sign only for a specified event or station.
- A delegation permits remote operation of named equipment, but excludes
  subdelegation or access to other stations.
- A particular assertion is valid only in a defined operating territory or
  location, or while supervision is present.

Time limitations are already represented by `nbf` and `exp`; a shorter validity
window needs no free-text exception. Constraints such as supervision or physical
location are useful only if the relying service can actually establish and
enforce them. Otherwise it must decline such a credential for this use.

Any mandatory constraint needs typed semantics and a versioning/criticality rule
that makes an older verifier reject it rather than ignore it. Unknown optional
descriptive claims may be ignored only where the accepted profile guarantees
that they do not qualify or contradict the authorization assertion. A future
restrictive profile must not reuse this profile's `vct` unchanged.

## 4. Cryptographic trust and offline status checking

Accept credentials only when the verified credential-signing key is authorized
by locally cached project trust material. Two trust paths are supported in the
design:

1. A valid certification path from a locally pinned project trustee to an
   issuer's credential-signing key.
2. A directly pinned issuer signing key or certificate with an explicitly
   configured administrative delegation.

Check signature validity, certificate/key usage, applicable validity and
revocation, and delegation scope. Scope may constrain credential types,
countries, CPS versions, or administrative roles. The initial service accepts
any credential within its issuer's authorized scope; it does not impose a
further country/class eligibility filter. Issuer names, certificate subject
names, `kid`, and remotely discovered keys are not independent trust anchors.

The backend must have a trustworthy link between the verified credential and
the signing-key/trust-path result. Neither an issuer-name match nor a
browser-supplied `verified` flag is an adequate substitute. Determine whether
the required policy is best implemented inside a supported walt.id verification
policy interface or through an authenticated server-side result containing
sufficient verification evidence.

Use a scheduled daily fetch for the trust list, public trust material, and
revocation/status artifacts. Authenticate downloaded material using pinned
project/issuer signing authority as appropriate; preserve TLS verification and
validate the artifact signatures, versions, and validity. Install an entire
verified update atomically and prevent rollback to an older accepted version.

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

All login-time verification uses a valid local snapshot. Do not fetch issuer
metadata, keys, trust chains, type metadata, CPS documents, CRLs, or credential
status on demand during a login. Unknown keys or status references are rejected
without a network fallback. A separate refresh process may acquire them for a
later attempt. This rule also covers automatic library fetches such as
certificate AIA/OCSP resolution and JOSE key URLs. A callback supplied by a
wallet is not a refresh instruction.

Local configuration supplies a maximum cache age and an operator-visible
refresh-failure policy. The proposed baseline is fail closed for new grants
when required material is missing, expired, or older than that maximum. A
failed refresh may leave the previous snapshot usable only while it remains
within those bounds. Do not silently extend signed validity dates. Daily
refresh implies revocation-detection latency of up to roughly one refresh
interval, plus any explicitly permitted refresh-failure window.

## 5. Initial local authorization policy

### 5.1 Admission

Admit a guest when all of the following hold:

1. The presentation meets the accepted credential profile, holder-binding,
   cryptographic trust, time, and cached status requirements above.
2. It contains one unambiguous canonical call sign.
3. That call sign is not on the configured access block list.

Permit admitted guests to call any configured local node. Reject nonlocal
destinations. There is no initial per-country, per-class, or per-node guest
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
  session_lifetime_seconds: 900  # proposed local default, subject to review
```

List and mode changes apply to newly established calls, including calls made
with an unexpired token issued before the configuration change. Recompute the
access decision and Rpt mode at each new call using the current local policy.
In this first draft, existing calls retain their mode until expiry or explicit
termination.
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

## 6. Opaque token and call lifecycle

### 6.1 Browser binding, presentation, and token issuance

Use an independent browser secret as well as the presentation transaction
identifier. One concrete same-origin flow is:

1. The browser creates a login transaction through a same-origin POST. The
   backend sets an unpredictable, host-only `Secure; HttpOnly; SameSite=Strict`
   session cookie, for example `__Host-csc-session` with `Path=/` and no Domain,
   Max-Age, or Expires attribute. An existing unexpired browser session can use
   its current secret. Reject cross-origin initiation; protect state-changing
   endpoints with an Origin check and a session-bound CSRF token.
2. The backend creates the walt.id verification session over localhost. In
   memory it records the public transaction identifier, a digest of the browser
   secret, verifier session identifier, expected nonce/audience, deadline, and
   pending/consumed state. The browser receives the request or QR-code data;
   it never receives the independent secret through a URL or QR code.
3. The wallet submits its presentation to the verifier. The backend obtains
   the authenticated outcome directly from the verifier over localhost and
   associates it with that existing transaction. The wallet callback does not
   need the browser cookie and does not itself authorize delivery of a token
   to whichever client made the callback. Validate any callback according to
   the verification protocol and protected internal interface.
4. The initiating page polls or completes through the same-origin backend with
   its cookie. The backend requires both the correct browser secret and the
   matching completed transaction, checks deadline/CSRF protection as
   appropriate, evaluates admission, and atomically consumes the transaction.
   Possession of the transaction identifier alone cannot claim the result.
5. Rotate session credentials on successful authentication and issue the
   opaque SIP token only to that authenticated browser session. Expire the
   pending record on cancellation or timeout. A consumed result cannot be
   redeemed again; completion retries must not issue additional grants.

Expose only the wallet-facing verifier routes needed by the presentation
protocol. Keep verifier result lookup, session management, and token issuance
control behind the backend/localhost boundary; the public transaction
identifier must not open a second route to claim the result.

Keep secrets out of redirect URLs, QR codes, browser logs, and audit logs. This
browser binding prevents another browser claiming an existing completed
transaction. It does not by itself prevent a person being tricked into
approving an attacker-initiated wallet request; wallet identification of the
verifier and deliberate approval of the intended login remain necessary.

Generate a cryptographically random opaque SIP token with at least 256 bits of
entropy. The browser receives the token, not an authoritative claim bundle.
Keep the token only in browser memory, not localStorage, IndexedDB, or
persistent cookies. The browser may receive display/control information such
as its authorized mode, but that information is never used as authority for
server decisions. Holder binding of the presentation does not make the later
Bearer token non-transferable; token confidentiality remains essential.

Keep a digest-indexed authorization record in memory. Its proposed contents are:

| Item | Purpose |
| --- | --- |
| Random grant identifier and token digest | Lookup and correlation without logging or storing the raw bearer token as the lookup key. |
| Canonical call sign and permitted SIP identity | Bind asserted SIP identity to verified credential facts. |
| Intended local SIP service | Prevent use at another service or host. |
| Issue and expiry times | Enforce the finite guest session. |
| Issuance-policy and trust/status snapshot versions | Explain the original grant decision; a new call also records its current local policy version. |
| Minimal credential/key/status references and normalized policy inputs | Recheck cached issuer/credential authorization for later calls without retaining the presentation or personal evidence. |

Opaque tokens have no client-readable authoritative claims. Whether the local
validation interface uses RFC 7662 introspection or a narrower protected
internal interface is an implementation decision. Do not describe a custom
interface as RFC 7662 unless it actually conforms.

The token/grant represents an in-memory guest session, not a single call. It
may be used to establish multiple calls during its validity, with fresh local
policy checks for each call. Hangup does not consume it. A fresh wallet
presentation is needed only when that session expires, the user explicitly
ends it, it loses authorization, or server-side state is lost.

Cap grant expiry at the earliest of local session lifetime, credential expiry,
applicable issuer/delegation validity, and the required trust/status snapshot's
acceptance deadline. The proposed local lifetime is 15 minutes, subject to
operator review. New access after expiry requires a fresh presentation; no
refresh-token or persistent-login mechanism is specified.

### 6.2 Call establishment

For a new call, the SIP user agent sends its access token using RFC 8898 Bearer
authentication on the INVITE, either initially or in response to a challenge.
It uses only the preconfigured local authorization server. A challenge must not
redirect it to an arbitrary third-party authorization server.

The SIP-side integration asks the backend to validate the token and resolve the
current grant. Before admitting the call, it checks expiry, the call-sign block
list, the intended local SIP service, the permitted SIP identity, the configured
local destination, and computes `rpt_mode` from the current policy. Reject
forged SIP identities or other caller-controlled identity fields that conflict
with the grant. Recheck current locally cached credential status and issuer/key
authorization using the grant's retained references and normalized policy
inputs. Newly observed revocation, delegation removal, or unusable required
cache material prevents new calls even with an otherwise unexpired token.
Successful rechecking never extends the grant's deadline. These checks do not
introduce continuous reevaluation of already established calls. Do not treat a
successful PJSIP endpoint lookup as proof that the INVITE is authenticated.

Bind the grant, expiry, current policy version, and `rpt_mode` to the actual
Asterisk channel/dialog.
Client-supplied headers or channel-variable names must not override the trusted
server decision. SIP transaction retransmission must remain correct; do not
accidentally treat a retransmitted INVITE as an unauthorized token replay.
This draft introduces no additional concurrent-call limit.

RFC 8898 section 2.1.2 still applies to the opaque token: select and validate a
mechanism that guarantees only authorized SIP endpoints can access it. Review
the browser/WSS/Apache/Asterisk path, local interfaces, and diagnostic logging.
The absence of general SIP proxying simplifies that analysis but is not itself
proof of compliance.

### 6.3 Expiry and cleanup

An admitted call cannot outlive its grant. Install a server-side expiry action
at establishment that terminates the channel at the grant deadline. Denying
subsequent INVITEs or deleting the token alone does not end an existing call.
Dialog updates must not extend access beyond that deadline. Teardown messages
must still be handled safely after authorization expires.

Remove expired grant and presentation records and discard completed call state.
A restart loses guest grants; tokens from before the restart must fail. If an
authorization component restarts independently of Asterisk, active-call expiry
must still be enforced and a defined failure action must prevent orphaned,
indefinitely authorized channels. Log the minimal decision and termination
events, not bearer tokens, SD-JWTs, disclosures, private keys, or biometric and
document evidence.

## 7. Implementation boundaries to prove

The current prototype still uses placeholder authentication and a PJSIP digest
password. The browser has `register: false` and the PJSIP wizard disables
registration, but the prototype does not implement RFC 8898 validation or this
authorization policy.

The current `from-webrtc` dialplan answers the call and enters `Rpt(...,P,...)`
without a server-selected mode or authorization-expiry action. Verify these
integration points before choosing implementation details:

- Browser SIP-stack support for RFC 8898 INVITE authentication.
- An inbound SIP Bearer-authentication/validation path that reaches the backend
  at the right point, before node access; existing realtime lookups alone do not
  establish this capability.
- A trusted way to attach the backend's decision to one channel, without using
  persistent user or per-call files.
- Selection of per-call `P`/`S` mode, command isolation, and the mode-dependent
  PTT sequences, including concurrent callers with different modes.
- Reliable call termination at expiry, including component restarts.

Use the existing `Rpt()` mode argument for command policy. For call expiry,
`TIMEOUT(absolute)` is a candidate mechanism. An already expired call must be
rejected, not given a zero timeout: zero disables that limit. Expiry must also
unkey transmission and clean up the associated node session. These are
investigation leads, not verified ASL3 behavior: `modules.conf` uses
`autoload = no` and explicitly disables `func_timeout.so`. Mode behavior,
linked-node behavior, and the interaction with `app_rpt` need real tests.

## 8. Acceptance examples

These are future integration-test requirements, not tests already executed.

| Scenario | Expected result |
| --- | --- |
| Valid holder-bound credential and authorized issuer, call sign not blocked | Permit call to a configured local node. |
| Valid club/delegated/class-licence call-sign assertion under the issuer's CPS | Apply the same admission rule; no personal-licence document requirement. |
| Correct issuer name but untrusted signing key, or wrong delegation scope | Reject. |
| Trusted issuer but missing holder proof, wrong audience/nonce, or replayed presentation | Reject. |
| Credential outside its assertion interval, revoked/suspended, or required cache stale | Reject without an on-demand issuer/status fetch. |
| Valid credential with blocked call sign | Reject regardless of full-control lists. |
| Default `P`; call sign not full-control-blocked | Permit call in mode `P`. |
| Default `P`; call sign full-control-blocked | Permit call in mode `S`, retaining PTT but not other phone commands. |
| Default `S`; call sign allowlisted and not blocked | Permit call in mode `P`. |
| Default `S`; call sign absent from allow list, or present in both lists | Permit call in mode `S`. |
| Browser changes claimed identity, target to a nonlocal node, or `rpt_mode` | Reject conflicting identity/destination; never accept a browser-supplied mode as authority. |
| Another browser knows a completed presentation's transaction identifier but lacks the bound cookie | Refuse completion and token delivery. |
| Initiating browser makes a second call within its valid guest session | No new wallet presentation; recheck current local policy and select the new call's mode. |
| Grant expires during an established call | Terminate the call at the deadline and reject later use of the token. |
| Policy changes after token issuance but before a new call | Apply the current access/full-control lists when establishing that new call. |
| A daily refresh revokes the credential or issuer after token issuance | Reject subsequent calls using the grant; existing calls retain their original expiry unless explicitly terminated. |
| Mandatory restriction from an unsupported profile/version | Reject rather than silently ignore it. |
| Verifier observes an unknown signing key or status reference | Reject using local data only; schedule any investigation/refresh separately. |

## 9. Decisions remaining before implementation

1. Settle the production `vct` name/version convention, CPS identifiers, and
   proposed claim shapes. The administration-native licence-class vocabulary
   and later equivalence mapping evolve independently and do not block this.
2. Select the exact SD-JWT VC/OpenID4VP release profile and credential-status
   format, including suspension semantics and signed freshness metadata.
3. Specify the signed project trust-list/delegation format, issuer certification
   rules, maximum cache age, and refresh-failure handling.
4. Confirm the proposed 15-minute grant lifetime and whether policy/revocation
   changes should terminate active calls before their existing expiry.
5. Prove the browser-binding, SIP Bearer, per-call mode/PTT, and expiry
   enforcement paths above.

## References

- [RFC 8898: Third-Party Token-Based Authentication and Authorization for SIP](https://www.rfc-editor.org/rfc/rfc8898.html), particularly sections 2.1.2 and 3.
- [SD-JWT-based Verifiable Credentials](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/).
- [SD-JWT VC type identifiers and metadata](https://github.com/oauth-wg/oauth-sd-jwt-vc/blob/main/draft-ietf-oauth-sd-jwt-vc.md).
- [RFC 4151: The tag URI Scheme](https://www.rfc-editor.org/rfc/rfc4151.html).
- [EUDI reference issuer PID type metadata](https://github.com/eu-digital-identity-wallet/eudi-srv-pid-issuer/blob/main/src/main/resources/vct/pid_v1.4.json).
- [OpenID for Verifiable Presentations 1.0](https://openid.net/specs/openid-4-verifiable-presentations-1_0.html).
- [walt.id Verifier API 2](https://github.com/walt-id/waltid-identity/tree/main/waltid-services/waltid-verifier-api2).
- [app_rpt mode documentation and implementation](https://github.com/AllStarLink/app_rpt/blob/22b60b5de6a7d99e3042f9b413d129dee3b97ad0/apps/app_rpt.c#L367).
- [Asterisk TIMEOUT implementation and documentation](https://github.com/asterisk/asterisk/blob/20/funcs/func_timeout.c).

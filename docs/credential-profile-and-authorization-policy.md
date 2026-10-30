# Draft: Call Sign Connect credential profile and SIP guest authorization

Status: discussion draft 0.8. This document specifies intended behavior; it does
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

Working references and implementation candidate:

| Component | Pin and status |
| --- | --- |
| SD-JWT VC | `draft-ietf-oauth-sd-jwt-vc-22`. |
| Underlying SD-JWT | RFC 9901, normatively required by draft -22, including its key-binding verification rules. |
| Presentation protocol | OpenID4VP 1.0 final, without compatibility with older drafts. |
| Credential status | `draft-ietf-oauth-status-list-21` (IETF Token Status List), replacing the earlier W3C Bitstring Status List proposal. |
| Verifier implementation candidate | walt.id identity `v1.2.0`, commit `ef516ecec4c79fd9fba6f1e8b226b52a4e8cf790`; use Verifier API 2, not the legacy API. Compatibility with the selected specification subset still needs testing. |
| Initial wallet target | Sphereon Wallet **0.9.0 on Android**. Inspected source baseline: commit `53335f5f0331df5c8708f3ecde1b7d1ddc7f9750`. Record the exact APK/build provenance during testing; support for other wallets is deferred. |

| Item | Requirement and meaning |
| --- | --- |
| `vct` | Required exact value `tag:callsignconnect.cloud,2026-10:call-sign-attestation:1`. |
| `iss` | Required issuer identifier; the project's default issuer uses `tag:callsignconnect.cloud,2026-10:issuer`. Resolve it only through supplied trust material, never remote issuer discovery. An identifier alone does not establish trust. |
| `iat` | Required issuance time. It does not replace the assertion's validity interval. |
| `nbf`, `exp` | Required start and end of the time interval for which the issuer attests the holder's right to assert the call sign. Accept only while `nbf <= now < exp`, with zero clock-skew allowance. |
| `cnf.jwk` | Required P-256 holder public key, bound by the issuer signature. This is part of the issued credential, not a new key for each presentation. |
| `status.status_list` | Required native draft-21 reference containing an integer `idx` and tag-URI `uri`. The entire reference is issuer-signed and not selectively disclosable; the list is supplied in the bundle. |

The CPS must ensure that the issued interval does not exceed the interval
supported by the evidence or delegation. These dates do not imply that a
personal licence exists. Separate source-document validity dates should be
added only if they convey a distinct fact the application needs.

Use the verifier's current clock without a grace period at either validity
boundary. Keeping that clock correct is an operational responsibility; early
rejection caused by a fast clock is not repaired by extending credential
validity. The wallet's clock is treated separately: its KB-JWT `iat` has the
one-hour tolerance below. That allowance never extends credential validity.

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

The wallet retains the holder private key. Its public counterpart is inside
the issuer-signed credential as `cnf.jwk`; neither is an ephemeral login key.
The holder key must remain usable for as long as the holder wants to present
that credential. Changing that key normally requires a newly issued
credential. The verifier needs the public key only while checking the
presentation and need not retain it as visitor data afterward.

For each new presentation, the wallet creates a **Key Binding JWT (KB-JWT)**:
a short signed proof using that holder private key. Its `aud` names the
intended verifier, `nonce` binds the pending request, `iat` records proof
creation, and `sd_hash` binds the exact presented SD-JWT and disclosures.
This proves current control of the holder key; the issuer's potentially
year-long `nbf`/`exp` interval answers a different question. A year-old proof
cannot authorize a new presentation merely because the credential is valid.

RFC 9901 requires an acceptable KB-JWT `iat` window as well as the fresh nonce.
Cap the complete pending presentation transaction at **900 seconds (15
minutes)**, measured on the server. At its deadline, forget an unclaimed nonce
and pending result, remove the temporary encryption private key, and refuse
completion. A successful transaction consumes its nonce once. Wallet-clock
tolerance does not extend this deadline.

Allow **3,600 seconds (one hour) of wallet clock skew in either direction**.
With finite numeric timestamps in seconds, require:

```text
transaction_deadline = transaction_started_at + 900
response_received_at < transaction_deadline
floor(transaction_started_at) - 3600 <= kb_iat <= response_received_at + 3600
```

Use a monotonic server timer for the elapsed transaction deadline, alongside
the wall-clock timestamps used for `iat` comparison. Completion/token delivery
must also occur before the same transaction deadline. The floor only
accommodates whole-second timestamp precision. Anchoring the lower bound to
transaction start allows the user to spend the full 15 minutes on the flow
even when the phone clock is an hour slow. At receipt this can admit a signed
timestamp almost 75 minutes old, while the actual proof is still bound to a
nonce issued less than 15 minutes ago. A fixed symmetric 60-minute proof-age
limit would incorrectly reject some such presentations.

`iat` is the holder's signed assertion of creation time, not an independent
trusted timestamp. Freshness/replay protection also depends on the local,
unpredictable, audience-bound, single-use nonce and bounded transaction.
Cookie resumption and subsequent calls use the remembered authorization and
do not create a new wallet presentation or require another KB-JWT (section 6).

The selected type identifier is
`tag:callsignconnect.cloud,2026-10:call-sign-attestation:1`. The name
describes an attestation about a call sign without implying an administration
issued a radio licence. The final `:1` denotes a schema/semantics version; the
tag's `2026-10`
date identifies the domain-control namespace and is not a credential issuance
date or expiry date. Use of that namespace assumes the
project controlled `callsignconnect.cloud` at the specified time.

The default issuer identifier is `tag:callsignconnect.cloud,2026-10:issuer`,
not an HTTPS issuer-metadata location. Bind this identifier to the certified
or directly pinned signing material supplied in the trust list. SD-JWT VC's
optional HTTPS JWT VC Issuer Metadata discovery mechanism is not used. The
certificate-based mechanism or an explicitly configured project key resolver
must verify the signature and its authorized trust path. Merely extracting a
public key from an `x5c` header does not establish that trust.

SD-JWT VC does not require an HTTPS `vct`. A tag URI has no automatic HTTPS
retrieval location. At issuance, the issuer supplies type metadata directly to
the wallet; the delivery mechanism is deferred until issuer integration. At
verification, the backend uses the supplied local metadata; do not enable a
walt.id metadata policy that performs discovery or HTTP retrieval. If the
chosen metadata includes integrity references, verify those against the exact
supplied bytes. Skipping integrity verification is not an offline resolver.
Correct operation does not depend on a prior or login-time remote fetch.
Check wallet support for issuance-time delivery. As a naming
comparison, the EUDI PID issuer uses `urn:eudi:pid:1` for Person Identification
Data; the type describes the attested subject matter rather than using the
generic word `credential` or `certificate`.

Draft -22 determines the `dc+sd-jwt` format and issuer JWT type; do not accept
the older `vc+sd-jwt` spelling as a compatibility fallback. RFC 9901 determines
the disclosure and key-binding machinery. The project requires holder binding,
including `cnf`, a verified `kb+jwt`, nonce/audience binding, and `sd_hash`.
The final OpenID4VP flow uses DCQL, not legacy Presentation Exchange requests.

Selected cryptographic choices:

- P-256 issuer and holder keys, with the holder public key directly in
  `cnf.jwk`.
- ES256 for issuer JWTs, holder KB-JWTs, Status List JWTs, and the verifier
  bundle. Use distinct bundle-signing, credential-issuance, and status-signing
  keys, including for the project's default issuer. The wallet's holder key
  has its separate proof-of-possession role. X.509 certificate-signature
  algorithms are a separate policy from these JOSE allowlists.
- SHA-256 for disclosures (`_sd_alg: "sha-256"`). Select explicit allowed
  algorithms; a supplied header cannot expand them.
- Zero clock-skew allowance for credential validity; a 15-minute pending
  transaction and one-hour wallet `iat` tolerance, as specified above.

These are explicit project decisions, not implicit consequences of selecting
draft -22. Test the selected subset with Sphereon Wallet 0.9.0 on Android and walt.id.
The selected flow uses WebPKI DNS-name authentication without verifier
pre-registration and `direct_post.jwt` with an ephemeral encryption key,
subject to the wallet support check in section 6.1. The response-encryption
algorithm pair remains separate from ES256 signature validation.

### 3.2 Application claims

The application claims for this iteration are `call_sign` and `cps`. Both are
covered by the issuer signature and must be disclosed during presentation.

| Proposed claim | Meaning |
| --- | --- |
| `call_sign` | One canonical call sign that the holder is entitled to assert under this attestation. It is the basis of the SIP identity and local list matching. |
| `cps` | Required object containing an immutable, version-specific `uri`. An optional `sha256` binds the exact CPS document bytes. |

`call_sign` must use uppercase ASCII letters and digits, have at most 63
characters, and full-match the single expression in
[call-sign-syntax.md](call-sign-syntax.md). The combined syntax envelope is
based on ITU Radio Regulations Nos. 19.50, 19.68, 19.68.1, 19.68A, and 19.69:
it includes the two-initial-digit prohibition and three-character prefixes.
The application length limit is separate from the regex and admits direct
use as a single ASCII DNS label. No ordinary/special classification or shorter
half-series suffix rule is retained or enforced; those assignment decisions
belong to the administration and issuer, not a structural verifier record.
Reject malformed or noncanonical signed values rather than silently fixing
them. Local list entries use the same canonical representation.

Do not constrain syntax validation by the prefix allocations in Appendix 42.
An issuer's authority to certify a prefix is determined by the configured
project trust list and its attached delegation material (section 4). This
separates syntactic validity from permission to assert a particular prefix.
Test the entire call sign independently against the issuer's permitted prefix
expressions using start-of-string matching. The trust list supplies literals
and restricted positive character classes, not full regex flexibility or
publisher-selected anchors. There is no captured structural prefix to compare.
Use `X10CSC` or other syntactically compliant signs synthesized under the
unallocated `X1` prefix for examples. Staging/test configurations can authorize
only such prefixes and exclude allocated real-world prefixes through trust
data, without source-code exceptions. Malformed signs remain invalid even in
staging; an unallocated prefix is a different issue.

The previous `X1CSC` example fails the literal No. 19.68 shapes: `X` is not
one of its permitted single-character identifications, and `X1` is not
followed by the required digit. `X10CSC` corrects the example without changing
the `X1` trust namespace or adding a source-code exception.

Portable prefixes/suffixes, alternative call signs, and operating-location
assertions are outside the profile. These are operating obligations beyond
the assertion the issuer certifies. No such additions are inferred from a
browser-supplied value.

The `vct` versions the claim meanings. The CPS URI versions the enrolment and
evidence procedure. They serve different purposes. A mutable URL such as
`/cps/current` is insufficient as the sole CPS reference. A project issuer's
reference is `https://callsignconnect.cloud/issuer/cp-cps-1.0`. No component needs
the CPS document to complete issuance or verification automatically, so it
need not be proactively delivered or cached. It must not be fetched during
login. The holder/subject may open its URI in a browser to read the procedure.

### 3.3 Illustrative disclosed claims

This is a logical claim-set illustration, not an encoded SD-JWT or an issuable
example. The type and default issuer identifiers and CPS URL are selected;
holder-key coordinates are placeholders. `X10CSC` is synthetic and requires an
appropriate test trust-list delegation. The status-list identifier and index
are illustrative and use the pinned IETF mechanism, not a project extension.

```json
{
  "iss": "tag:callsignconnect.cloud,2026-10:issuer",
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
  "call_sign": "X10CSC",
  "cps": {
    "uri": "https://callsignconnect.cloud/issuer/cp-cps-1.0"
  },
  "status": {
    "status_list": {
      "idx": 42,
      "uri": "tag:callsignconnect.cloud,2026-10:status-list:1"
    }
  }
}
```

The per-credential status reference identifies **which list**, **which entry**,
and the status mechanism. `idx` is a nonnegative JSON integer, not a decimal
string. Require the whole `status` reference directly in the issuer-signed
claims, not selectively disclosable; reject it if missing or malformed.
Assign indices without deriving them from call signs or other identity data.

Resolve `uri` exactly against an entire Status List JWT included in the
authenticated bundle. The list JWT's `sub` must equal that identifier. Draft
-21 permits URI schemes other than HTTPS and an agreed alternative distribution
mechanism; the project uses tag identifiers and supplied local resources. No
match means rejection, with no network fallback. Check the authorized list
signer, signature, index bounds, bit width, and any hard expiry.

An illustrative Status List JWT has protected `typ: "statuslist+jwt"` and a
payload like this (the compressed list is a placeholder):

```json
{
  "sub": "tag:callsignconnect.cloud,2026-10:status-list:1",
  "iat": 1793318400,
  "ttl": 86400,
  "status_list": {
    "bits": 2,
    "lst": "<base64url-zlib-compressed-status-values>"
  }
}
```

Draft -21 defines status values rather than a W3C `statusPurpose` field:

| Value | Meaning and initial verifier behavior |
| --- | --- |
| 0: VALID | Eligible for the remaining credential/authorization checks. |
| 1: INVALID | Reject; may represent revocation, cancellation, or similar invalidity. |
| 2: SUSPENDED | Reject while temporarily invalid, if the issuer uses this state. |
| Other/unsupported value | Reject; never treat an unknown value as valid. |

One bit can encode only 0/1. Use two bits so later suspension can be
represented without changing an existing list's bit width; the initial access
decision admits only zero either way. The IETF draft does not impose an
irreversible transition for INVALID. An issuer policy may make revocation
terminal and require reissuance; EUDI's ARF does so for its own credentials.
Suspension can be useful during a reversible investigation or temporary
withdrawal, but is not necessary for this ASL3 access rule. Neither revocation
nor suspension instructs a relying service to delete accounts, stored objects,
or other business data. Those lifecycles are separate policy decisions.

The list encodes a current credential status, not a complete historical
record of when a station-log signing key was trustworthy. Long-term log
verification may need effective revocation times, reasons and retained
evidence; a later suspension/revocation alone does not determine whether an
earlier log signature was valid. That separate use case is deferred.

For indefinite holdover, project-controlled Status List JWTs deliberately
omit their optional `exp`, retaining local freshness enforcement
and `ttl` refresh guidance. If a list includes `exp`, draft -21 requires it to
be respected; holdover cannot silently override it while claiming conformance.
See [verifier-bundle-format.md](verifier-bundle-format.md) for the rationale.

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
against at least one of that issuer/key's permitted `prefixes` expressions at
the beginning of the string. Prefix matching is a separate boolean decision
and retains no call-sign type. The syntax validator does not
contain the global prefix-allocation table. Production and staging/test trust
lists can therefore admit disjoint prefix sets through data alone. Issuer
names, certificate subject names, `kid`, and remotely discovered keys are not
independent trust anchors.

Key roles state what a trusted key may sign. Credential keys attest the
credential claims; status-list keys sign the specified status lists; project
bundle keys authenticate the distribution snapshot. A key authorized for one
role is not automatically authorized for another. Holder keys prove possession
and are bound by individual credentials, not listed as issuer authorities.
Use distinct keys for issuance, status and bundle signing. A separate status
key must also be scoped to the lists whose values it can authorize.

The backend must have a trustworthy link between the verified credential and
the signing-key/trust-path result. Neither an issuer-name match nor a
browser-supplied `verified` flag is an adequate substitute. Use walt.id's
protected server-side result to correlate the successful issuer-signature
policy's public key and verified data with the expected credential/query and
successful presentation/holder-binding checks. The backend then enforces
local issuer/key authority, metadata, status and admission rules. An internal
policy plugin is not assumed: v1.2.0's credential-policy classes are sealed.

The trust list and attached material include everything needed to identify
trusted issuers and validate their signing authority. Supply type metadata
locally as described in section 3.1. A provisioned set must allow correct
operation without first fetching remote metadata or other referenced objects.

### 4.1 Publication roles and supplied status lists

The project separates publication by role:

| Location | Contents |
| --- | --- |
| `https://callsignconnect.cloud/issuer/` | Material published by or for the default issuer, including `cp-cps-1.0`, except material required for automated verifier processing. |
| `https://callsignconnect.cloud/verifiers/` | Trust list, attached signing/trust material, complete status information, and other public material needed for automated verifier processing. |
| Other paths under `https://callsignconnect.cloud/` | General project material. |

The issuer's tag identifier is independent of its publication directory.
Neither that identifier nor the directory grants a metadata-discovery route.
All automated issuer information comes from the trust list and attached
material. Human access to the CPS is separate from verifier processing.

Use tag URIs for identifiers that do not require HTTPS retrieval to perform
their function: issuer, credential type, status-list identity, bundle/schema
identity, and stable key identifiers. Keep HTTPS URLs where fetching is the
intended operation: the scheduled bundle download and human-readable CPS URI.
Do not invent an HTTPS object identifier just because a local resolver could
avoid following it.

Use the pinned IETF Token Status List mechanism. Include the complete signed
Status List JWT and required verification material in the trust bundle, not
only a reference. Include every list needed by the accepted credentials and
preserve its tag `sub` identifier for local lookup. Verification does not
contact an issuer or dereference a status identifier over the network.

The list signer must be authorized for the relevant credential status. It may
be distinct from the credential issuer only through explicit trust delegation.
The bundle's authenticated association with a list and the list JWT's own
signature must both be checked. No JSON-LD/context-processing mechanism is
required. The selected single-file compact-JWS distribution, proposed
trust-list schema, and atomic-installation procedure are in
[verifier-bundle-format.md](verifier-bundle-format.md).

For this integration, assume the authorized bundle-verification certificates
are provisioned locally. One valid ES256 bundle signature under any one of
their public keys suffices. Project trustee/root/intermediate issuance,
renewal and distribution mechanisms are outside this task; the bundle cannot
supply its own trust anchor. These keys remain distinct from the default
issuer's credential- and status-signing keys.

### 4.2 Refresh, freshness, and holdover

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
- Invalidity or suspension of an individual credential, represented by the
  complete IETF Status List Token attached to the trust list.

The last item is not the same format or object as an X.509 CRL. Its status-list
format and native SD-JWT reference are selected. A tag status identifier is
resolved solely through supplied resources, never remote retrieval.

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
| Normal (default) | Maximum accepted snapshot age is 73 hours. Reuse it during refresh failures within that window; after it, reject new authorizations, resumptions, and calls until a successful refresh. This allows two consecutive missed 24-hour refresh attempts. The proposed signed bundle time determines age; re-fetching old signed bytes must not reset it. |
| Manual indefinite holdover | An administrator deliberately selects the last verified snapshot for offline operation. Treat that snapshot as authoritative without an age cutoff for the duration of the selected mode. Do not enter this mode automatically after refresh failure. |

Holdover is intended for planned Field Day, EmComm, and beyond-grid operation.
It accepts the risk of revocations or trust changes not learned after the held
snapshot. It does not undo revocations already present in that snapshot, accept
invalid signatures, expand an issuer's prefix authority, waive holder binding,
or extend a credential's own `nbf`/`exp` interval. Normal certificate/key and
delegation validity checks also remain separate from cache freshness. Log the
administrator's holdover selection and when normal operation resumes, and make
the active mode visible to the administrator.

Distinguish refresh guidance from a hard validity limit. Local snapshot age,
Status List Token `ttl`, and cached CRL refresh information are handled by the
chosen normal/holdover freshness policy. An explicit Status List JWT `exp`
must still be checked under pinned draft -21 and cannot be overridden by
holdover. Project-controlled lists intended for indefinite holdover
omit that optional expiry, with the availability rationale recorded
in the bundle design. This intentionally departs from a RECOMMENDED claim,
not a mandatory one. Credential and issuer/delegation validity remain separate
checks. Neither mode repairs missing material or invalid signatures.

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
presentation:
  transaction_lifetime_seconds: 900
  wallet_iat_clock_skew_seconds: 3600
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
| Pending presentation transaction | Backend/verifier memory and a browser-binding cookie; at most 15 minutes, single-use, with unclaimed nonce/result and ephemeral private key forgotten at the deadline. |
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
   pending/consumed state. Set the deadline to 15 minutes from transaction
   creation, shared with the verifier session expiry. The browser receives
   request/QR-code data, never the independent secret in a URL or QR code.
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

#### Selected OpenID4VP request and response flow

The initial supported wallet target is Sphereon Wallet 0.9.0 on Android. The
selected flow authenticates the verifier by its WebPKI DNS name without
pre-registration and returns an encrypted presentation directly to the
verifier. Verify these capabilities against an identified Android build
before claiming interoperability; a feature in an SDK or development branch
does not establish that it is available in the installed application.

| Choice | Selected behavior |
| --- | --- |
| Verifier/client identification | `x509_san_dns` binds a signed request to the verifier's DNS SAN and a WebPKI chain trusted by the wallet. No verifier pre-registration or separate wallet project-root provisioning is assumed. |
| Request transport and signing | An HTTPS `request_uri` lets the wallet retrieve the request, including a signed Request Object when the identification method permits it. This deliberate protocol fetch is distinct from forbidden issuer/status/metadata discovery. |
| `direct_post.jwt` response | The wallet POSTs an encrypted JWE response envelope to the verifier's HTTPS `response_uri`, using a fresh per-transaction encryption key advertised in the signed request. This is response encryption, not an additional response signature. Issuer and holder signatures inside the presentation remain mandatory. |

The development verifier uses
`client_id: x509_san_dns:csc-dev.rtdev.cloud`, an ES256-signed Request Object
with its certificate chain in `x5c`, an HTTPS `request_uri`, and a same-host
`response_uri`. The wallet must trust the request-signing certificate chain
and check its DNS SAN; a certificate trusted by our backend alone is
insufficient. The wallet must present the authenticated domain as the service
identity to the user. Request-signing credentials have a separate role from
issuer, holder and bundle keys. Merely using an HTTPS request URL does not
replace authentication of the signed OpenID4VP request.

For encrypted responses, ECDH-ES/P-256 with A128GCM remains the candidate
algorithm pair pending the wallet/release capability check. The encryption
keypair is ephemeral and distinct from the credential's holder `cnf.jwk`.
Keep its private key only in verifier memory until completion or the 15-minute
deadline. Do not silently downgrade to plaintext `direct_post` or an older
presentation protocol if the selected wallet does not support this flow.
The Digital Credentials API and other wallets are deferred.

The operational client identifier follows OpenID4VP's defined identification
method; an arbitrary `tag:` client ID does not automatically authenticate the
verifier. Credential issuer/type/status/bundle identifiers remain tag URIs.
For this non-DC-API flow, use the actual full client identifier when checking
the holder proof audience. DC API instead uses its defined `origin:` audience.
Request signing and response encryption do not replace the browser-bound
transaction above or by themselves prevent QR-code relay/phishing.

#### User-facing failures

Give the initiating browser a useful result through its existing protected
result/polling route. Distinguish an expired 15-minute transaction, wallet
cancellation, a verified proof timestamp outside the one-hour clock allowance,
and an expired or otherwise unacceptable credential. For example:
"Your wallet's reported signing time is outside the allowed range. Check
your phone's date, time and automatic time setting, then try again."
Do not assert that the phone clock is certainly the cause. Show that specific
diagnosis only after the relevant signatures, audience and nonce checks
support it. Otherwise use a general presentation failure message. Do not
expose tokens, keys, raw credentials, trust-store internals or exception dumps.

OpenID4VP's `error`/`error_description` Authorization Error Response primarily
travels from wallet to verifier. It is not a portable verifier-to-wallet
user-message channel. The direct-post response can carry a `redirect_uri`
that the wallet follows, allowing a verifier-hosted result page; unrecognized
extra JSON parameters must be ignored. Whether a wallet displays an HTTP
failure's description itself is application-specific. Do not depend on that
behavior for understandable failures.

The inspected Sphereon mobile source follows a successful callback's JSON
`redirect_uri` by opening the browser. It does not display arbitrary extra
message fields. Its SDK's non-2xx error handling can show only generic HTTP
status text, so returning a descriptive JSON error body is insufficient to
guarantee readable guidance inside that wallet.

The initiating browser remains the reliable place to show its authenticated
transaction result. A wallet-side redirect page, if enabled, may show suitable
generic guidance but does not receive the initiating browser's authorization
or SIP token. Coordinate any callback-level denial/redirect with the backend:
walt.id can acknowledge successful presentation processing before our local
admission policy has decided whether to grant access. "Presentation received"
and "access granted" are distinct outcomes.

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
- Local-only resolution of the complete bundled IETF Status List Token, with a
  required reference/presence check and no silently skipped status policy.
- Sealed-cookie resumption with no persistent server-side visitor record.
- Selection of per-call `P`/`S` mode, command isolation, and the mode-dependent
  PTT sequences, including concurrent callers with different modes.
- Rejection of new calls after token expiry without terminating existing
  calls, including correct existing-dialog behavior and component restarts.

Use the existing `Rpt()` mode argument for command policy. Do not add an
authorization-expiry call timer. Mode behavior, linked-node behavior, PTT,
normal call-end cleanup, and the interaction with `app_rpt` need real tests.

The tag issuer and offline status policy require explicit verifier integration.
The v1.2.0 key resolver can extract a verification key from an `x5c` header for
a tag issuer. This provides a candidate integration route without forking:
require the expected presentation and successful signature/holder-binding
results, obtain the verified key and claims through the protected management
API, and enforce trust/status/metadata/admission in our backend. An `x5c`
certificate supplies a public key, not trust; only the local snapshot or
explicit local delegation can authorize it. A tag plus `kid` alone does not
automatically select a locally pinned bare key. Supporting that representation
would require an explicit-key library-composition path or resolver change;
it is not a deployment-only configuration option already established.

Do not enable the built-in remote status policy for this path. It owns a
fetcher, can retrieve on a cache miss, and can report status policy unavailable
when the reference is absent. Our backend instead requires the reference,
validates the supplied list and checks its entry, enforcing normal/holdover
freshness itself. Built-in web caching does not supply the immutable snapshot
contract. Likewise, a metadata option that skips integrity checking is not a
substitute for checking the supplied metadata. Test with presentation-time
outbound retrieval blocked. These admission checks require integration code,
but not a new OpenID4VP/SD-JWT cryptographic implementation.

The v1.2.0 SD-JWT VC README cites **draft -03**; no coherent release-wide newer
VC draft conformance claim was established. The code nevertheless accepts
`dc+sd-jwt`, uses final OpenID4VP/DCQL and RFC 9901 disclosure checks/tests,
and checks KB-JWT signature, type, audience, nonce, hash and freshness. The
status codec tests cite status-list **draft -20**, not a complete -21
conformance claim. These are documentation/coverage gaps, not evidence that
API 2 only implements VC draft -03. Do not downgrade the whole credential
profile to -03 solely on that README; keep -22 as the working reference
until selected-subset tests establish an actual incompatibility. OpenID4VP
1.0, P-256/ES256/SHA-256 and the backend's native draft-21 status checks
remain selected. Pin the deployment artifact digest when packaging it; do
not silently rely on behavior inspected only on `main`. These are
release-source findings, not an end-to-end verifier validation already run.

Time-policy defaults also need explicit integration. The release's credential
expiry/not-before policies allow two seconds of skew by default and do not
enforce this profile's required claim presence. The backend must require
finite numeric `nbf`/`exp` claims and enforce `nbf <= now < exp` independently.
The KB-JWT policy's default five-minute setting is a symmetric freshness
window. Configure `maxAgeMinutes: 76` for `dc+sd-jwt/kb-jwt_iat-check`, then
have the backend enforce the exact transaction/skew window above. Sixty
minutes would reject some valid 15-minute transactions from slow phone clocks.
The extra minute above 75 accommodates timestamp precision in this upstream
guard; it does not expand the backend's exact transaction/skew window.
Set `core_flow.expiration_duration` to `PT15M` or use a shared explicit
deadline. Replacing the VP-policy list must preserve the other required
signature, audience, nonce, disclosure-hash and time checks; configuring this
one policy is not permission to omit them. An upstream success cannot waive
the backend's stricter admission checks.

The pinned verifier supports `core_flow.encrypted_response: true`, generates
a fresh P-256 response-encryption key for the direct-post session and advertises
its public key. It supports ECDH-ES with A128GCM/A256GCM; restrict the advertised
and accepted algorithm set to the eventual wallet-tested choice. Its
`x509_san_dns` flow requires a signed request, `x5c` and the matching signing
key. These service capabilities do not establish Sphereon Android support or
the wallet's acceptance of a public WebPKI certificate chain.

Sphereon capability evidence is mixed. The selected target is version 0.9.0;
the inspected public mobile source baseline is commit
`53335f5f0331df5c8708f3ecde1b7d1ddc7f9750`, using SDK 0.40.1. Record the
exact APK/build provenance when testing this target. The older public GitHub
release v0.7.0 uses different dependencies and is not the selected target.
The newer SDK contains final OpenID4VP/DCQL, `dc+sd-jwt` and encrypted
response support, but the following source findings need reproduction:

- The app's request-certificate trust registry supplies Sphereon/Funke and
  user-added anchors. Android/system WebPKI roots are not established as
  request-object trust anchors merely because HTTPS retrieval succeeds.
- Its first-contact path passes the raw non-DID client identifier to
  `new URL(...)`; `x509_san_dns:csc-dev.rtdev.cloud` is not a URL accepted
  by that parser. This can obstruct first use without a saved contact.
- SDK 0.40.1's JWE creation path appears to omit the selected recipient
  `kid`. Final OpenID4VP and the pinned verifier require the expected key
  identifier; encryption support alone does not establish compatibility.

These are source-inspection findings, not an Android interoperability test.
Record the installed build and test the exact selected flow before treating
Sphereon support as proved. Importing project roots or pre-registering a
contact is not evidence that the selected no-registration WebPKI flow works.

## 8. Acceptance examples

These are future integration-test requirements, not tests already executed.

| Scenario | Expected result |
| --- | --- |
| Valid holder-bound credential and authorized issuer, call sign not blocked | Permit call to a configured local node. |
| Valid club/delegated/class-licence call-sign assertion under the issuer's CPS | Apply the same admission rule; no personal-licence document requirement. |
| Correct issuer name but untrusted signing key, or wrong delegation scope | Reject. |
| Syntactically valid `X10CSC` and issuer permitted prefix `X1` in staging | Permit if otherwise valid; no source-code exception for `X1`. |
| Earlier example `X1CSC` | Reject the malformed shape; do not exempt the prototype's old placeholder identity. |
| Syntactically valid allocated prefix outside the staging issuer's delegation | Reject, even if Appendix 42 assigns that prefix in the real world. |
| Malformed or nonuppercase signed `call_sign` | Reject regardless of prefix delegation. |
| Syntactically matching call sign with 64 characters | Reject by the separate 63-character limit. |
| `3DN0ABC` and issuer prefix `3D[N-Z]` | Permit the syntax/prefix checks without a half-series classification. |
| `G9V1XX` and issuer prefixes `9V`, `S6` | Reject: a substring occurrence is not an authorized prefix. |
| Trusted issuer but missing holder proof, wrong audience/nonce, or replayed presentation | Reject. |
| Credential remains valid for months but its KB-JWT belongs to an old transaction | Reject the presentation; credential lifetime does not extend a proof's freshness window. |
| Presentation or browser completion arrives at/after the transaction's 15-minute deadline | Reject and require a new transaction, irrespective of wallet `iat` tolerance. |
| Proof is signed near transaction start on a phone one hour slow and received 14 minutes later | Permit the proof-time check if within the transaction/skew bounds; do not apply a fixed 60-minute proof-age cutoff. |
| Validly signed, correctly bound proof reports a time outside the permitted wallet-clock window | Reject and give the bound browser guidance to check the phone clock. |
| Verifier's clock has reached credential `exp`, even by a fraction of a second | Reject new authorization without expiry grace. |
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
| Default issuer uses the tag identifier, and its signing key is authorized by supplied material | Verify without HTTPS issuer discovery; do not infer trust from the identifier. |
| Credential refers to an IETF Status List Token by tag identifier | Match its `sub` and check the numeric `idx` using the exact bundled token, without a request. |
| Required status reference is missing or the referenced list is absent | Reject; a skipped/unavailable status policy is not success. |
| A list includes `exp` and is expired during manual holdover | Reject that list under draft -21; holdover is not an expiry bypass. |

## 9. Decisions remaining before implementation

1. Test draft -22/RFC 9901 and final OpenID4VP 1.0's selected subset against
   walt.id v1.2.0, including the selected P-256/ES256/SHA-256 choices. Prove
   Sphereon Wallet 0.9.0 Android WebPKI request identification, signed requests and
   `direct_post.jwt` with ephemeral encryption. Record the tested wallet build
   and select the encryption algorithm pair. Transaction lifetime is 15
   minutes; wallet `iat` tolerance is one hour in each direction, while
   credential validity has no grace period.
2. Implement the accepted boolean call-sign expression, separate 63-character
   bound, and verifier-enforced prefix matching. Finalize the proposed limited
   prefix-pattern grammar and input-size bounds. Keep `prefixmatch` in the
   illustration, but use the older `match` API for Debian 13's Python runtime.
   Two-bit status width and deliberate omission of optional
   list expiry for project holdover-compatible lists are selected.
3. Finalize the draft JSON-in-JWS trust-list schema, prefix/list delegation,
   local metadata/status adapters, publication-time age measurement, and atomic
   refresh/holdover installation mechanics. Assume authorized bundle signer
   certificates are provisioned locally; trustee certificate infrastructure is
   outside this task. The 24-hour interval and 73-hour maximum age remain selected.
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
- [SD-JWT VC, pinned draft -22](https://github.com/oauth-wg/oauth-sd-jwt-vc/blob/draft-ietf-oauth-sd-jwt-vc-22/draft-ietf-oauth-sd-jwt-vc.md).
- [SD-JWT, RFC 9901](https://www.rfc-editor.org/rfc/rfc9901.html).
- [IETF Token Status List, pinned draft -21](https://github.com/oauth-wg/draft-ietf-oauth-status-list/tree/draft-ietf-oauth-status-list-21).
- [EUDI ARF credential-revocation requirements](https://github.com/eu-digital-identity-wallet/eudi-doc-architecture-and-reference-framework/blob/main/docs/annexes/annex-2/annex-2.02-high-level-requirements-by-topic.md#VCR_04).
- [RFC 4151: The tag URI Scheme](https://www.rfc-editor.org/rfc/rfc4151.html).
- [EUDI reference issuer PID type metadata](https://github.com/eu-digital-identity-wallet/eudi-srv-pid-issuer/blob/main/src/main/resources/vct/pid_v1.4.json).
- [OpenID for Verifiable Presentations 1.0 final](https://openid.net/specs/openid-4-verifiable-presentations-1_0-final.html).
- [walt.id identity v1.2.0 release](https://github.com/walt-id/waltid-identity/releases/tag/v1.2.0).
- [walt.id Verifier API 2 v1.2.0](https://github.com/walt-id/waltid-identity/tree/v1.2.0/waltid-services/waltid-verifier-api2).
- [walt.id v1.2.0 key resolver](https://github.com/walt-id/waltid-identity/blob/v1.2.0/waltid-libraries/credentials/waltid-credential-key-resolver/src/commonMain/kotlin/id/walt/credentials/keyresolver/Crypto2JwtKeyResolver.kt).
- [walt.id v1.2.0 web fetching](https://github.com/walt-id/waltid-identity/blob/v1.2.0/waltid-libraries/web/waltid-web-data-fetching/src/commonMain/kotlin/id/walt/webdatafetching/WebDataFetcher.kt).
- [walt.id v1.2.0 presentation verification policies](https://github.com/walt-id/waltid-identity/blob/v1.2.0/waltid-libraries/credentials/waltid-verification-policies2-vp/src/commonMain/kotlin/id/walt/policies2/vp/policies/VPVerificationPolicyManager.kt).
- [walt.id v1.2.0 SD-JWT README](https://github.com/walt-id/waltid-identity/blob/v1.2.0/waltid-libraries/sdjwt/waltid-sdjwt/README.md).
- [walt.id v1.2.0 signature policy and verified-key result](https://github.com/walt-id/waltid-identity/blob/v1.2.0/waltid-libraries/credentials/waltid-verification-policies2/src/commonMain/kotlin/id/walt/policies2/vc/policies/CredentialSignaturePolicy.kt).
- [walt.id v1.2.0 server-side session view](https://github.com/walt-id/waltid-identity/blob/v1.2.0/waltid-libraries/protocols/waltid-openid4vp-verifier/src/commonMain/kotlin/id/walt/verifier2/data/Verification2Session.kt).
- [Sphereon mobile certificate trust registry, inspected commit](https://github.com/Sphereon-Opensource/ssi-mobile-wallet/blob/53335f5f0331df5c8708f3ecde1b7d1ddc7f9750/src/agent/trustAnchorRegistry.ts).
- [Sphereon mobile request/contact and callback handling, inspected commit](https://github.com/Sphereon-Opensource/ssi-mobile-wallet/blob/53335f5f0331df5c8708f3ecde1b7d1ddc7f9750/src/services/machines/siopV2MachineService.ts).
- [Sphereon SDK 0.40.1 encrypted response creation](https://github.com/Sphereon-Opensource/SSI-SDK/blob/e51d450fceab02b6da01c8b88de9532a09d1e913/packages/siopv2-oid4vp-op-auth/src/session/OpSession.ts).
- [Sphereon SDK 0.40.1 JWE implementation](https://github.com/Sphereon-Opensource/SSI-SDK/blob/e51d450fceab02b6da01c8b88de9532a09d1e913/packages/jwt-service/src/functions/JWE.ts).
- [app_rpt mode documentation and implementation](https://github.com/AllStarLink/app_rpt/blob/22b60b5de6a7d99e3042f9b413d129dee3b97ad0/apps/app_rpt.c#L367).

# Draft: verifier resource bundle

Status: proposal for review. This defines a possible distribution format, not
an implemented endpoint or a new credential format. The credential profile is
in [credential-profile-and-authorization-policy.md](credential-profile-and-authorization-policy.md).

## 1. Requirements and recommended container

Fetch one HTTPS resource, for example
`https://callsignconnect.cloud/verifiers/bundle.jws`, as a single file. The
normal refresh interval is 24 hours. After complete download and validation,
accept the entire snapshot atomically; no request triggered by a credential
presentation resolves additional resources.

The recommended initial container is a **JSON payload inside a compact JWS**.
The payload contains the trust list and all resources directly. Use an existing
JOSE implementation to sign and verify the exact JWS payload bytes. JSON
canonicalization is not needed when verifying those original bytes. This is
a signed data file, not an archive that must be unpacked before validation.

| Option | Trade-off |
| --- | --- |
| Compact JWS containing JSON and complete embedded resources | Fits existing JOSE tooling; one signature/file; no archive paths or extraction semantics. Base64url adds size overhead, normally acceptable for this bundle. Recommended initially. |
| ZIP or tar.gz containing resources and an embedded signed manifest | Appropriate if there are many binary resources. The manifest must bind every accepted file by identifier, size, and digest. Reject duplicate names, unlisted content, traversal paths, links, and decompression excesses; validate before installation. More machinery than the initial bundle needs. |
| CMS SignedData or COSE_Sign1 containing the snapshot | Standard single-file signed containers. CMS fits X.509 tooling; COSE/CBOR is compact. Both add another protocol/tooling family without an immediate need here. |

A detached signature beside the bundle would require a second response unless
both are packaged in a single outer file. HTTPS authentication remains enabled
even when the bundle has its own signature. Do not place secrets or private
keys in this public artifact.

## 2. Signing authority

Provision the project trustee/bundle verification key independently in the
verifier's deployment configuration. A key delivered inside an otherwise
untrusted candidate bundle cannot authorize that bundle's own signature.

An initial recommendation is ES256 with a P-256 signing key. Keep the bundle
signing role distinct from credential issuance and status signing, even if
the project operates all three. A signed issuer entry delegates authority
from the project trustee to that issuer/key; a separate X.509 delegation
certificate is optional if this signed-list delegation format is accepted.
Existing issuer certificates can still be included for the verifier's
certificate-based key-resolution path.

The protected JWS header should contain a fixed application type, the approved
algorithm, and a signer identifier such as
`tag:callsignconnect.cloud,2026-10:trustee-key:1`. Treat the identifier as a
lookup into provisioned keys, never a network location or permission to trust
an embedded key. Algorithm acceptance is configured per role; the candidate
cannot expand it by choosing a header value.

Signer rotation must be authenticated by an already trusted authority or
delivered through administrator configuration. A single compact JWS uses one
signer; if simultaneous signatures become necessary, JWS General JSON
Serialization is an alternative container revision. Do not require a root-key
change merely to rotate an issuer's credential-signing key.

## 3. Trust-list contents

Yes: a JSON list of issuers, public keys, and prefixes is the right starting
point. A useful minimal record also needs an unambiguous issuer identifier,
key identity/role, credential-type scope, and enough formation information to
apply the call-sign rules. The display name is informational.

Proposed fields:

| Field | Purpose |
| --- | --- |
| Bundle schema identifier | Exact data-format/version contract; reject unsupported schemas. |
| Bundle identifier | Stable tag URI for this stream, separate from its HTTPS download URL. |
| Monotonic sequence | Detect rollback relative to the last accepted snapshot. Re-fetching the same snapshot does not advance it. |
| Signed publication time | Determine snapshot age; downloading old signed bytes again must not make them fresh. |
| Issuer identifier and display name | Match the declared issuer; provide a human-readable label without making the label a trust anchor. |
| Authorized signing keys/certificates | Public material and stable key identity, with explicit credential/status-signing roles and any validity bounds. |
| Credential-type and prefix delegation | Limit which type and call-sign namespace each key can attest. |
| Complete resource map | Type metadata, signed Status List Tokens, and any other material required by validation, indexed by tag identifiers. |

Key rotation requires more than one simultaneously listed key when old
credentials remain valid. Removing or restricting a key changes subsequent
authorization according to the existing snapshot/call policy. Where scope is
attached to a key, another key under the same issuer does not inherit it
implicitly. Validate uniqueness and conflicting delegations when accepting
the bundle, rather than allowing parser order to resolve them.

Call-sign prefix entries should specify a formation rule as well as a prefix.
The [call-sign syntax draft](call-sign-syntax.md) explains why half-series and
temporary extended-suffix permissions cannot be inferred from the first
successful regular-expression match. No Appendix 42 allocation database is
compiled into the application.

## 4. Illustrative payload

This is an abridged proposal with placeholder key coordinates and status JWT,
not a usable or signed bundle. Identifiers are tag URIs; only the outer
distribution endpoint and human-readable CPS reference need HTTPS URLs.

```json
{
  "schema": "tag:callsignconnect.cloud,2026-10:verifier-bundle:1",
  "id": "tag:callsignconnect.cloud,2026-10:verifier-bundle",
  "sequence": 17,
  "issued_at": 1793318400,
  "issuers": [
    {
      "id": "tag:callsignconnect.cloud,2026-10:issuer",
      "name": "Call Sign Connect default issuer",
      "keys": [
        {
          "id": "tag:callsignconnect.cloud,2026-10:issuer-key:1",
          "jwk": {
            "kty": "EC",
            "crv": "P-256",
            "x": "<public-key-x>",
            "y": "<public-key-y>"
          },
          "uses": ["credential", "status-list"],
          "credential_types": [
            "tag:callsignconnect.cloud,2026-10:call-sign-attestation:1"
          ],
          "prefix_rules": [
            {
              "prefix": "X1",
              "formation": "two-character",
              "temporary_extended_suffix": false
            }
          ]
        }
      ]
    }
  ],
  "resources": [
    {
      "id": "tag:callsignconnect.cloud,2026-10:call-sign-attestation:1",
      "media_type": "application/json",
      "content": {
        "vct": "tag:callsignconnect.cloud,2026-10:call-sign-attestation:1"
      }
    },
    {
      "id": "tag:callsignconnect.cloud,2026-10:status-list:1",
      "media_type": "application/statuslist+jwt",
      "content": "<complete-signed-Status-List-JWT>"
    }
  ]
}
```

This example gives one issuer key both credential and status roles explicitly;
it does not make that the required key arrangement. The bundle trustee key is
not taken from this payload. Any X.509 chains, additional issuer metadata,
and further status lists needed by the selected verifier must also be supplied.
The precise local adapter schema is to be finalized against walt.id v1.2.0.

An outer bundle signature authenticates the snapshot and its associations.
The embedded Status List JWT still has its own signature and authorized signer;
validate it as required by the pinned status-list specification. Preserve its
original compact encoding instead of parsing and re-signing it during packing.

## 5. Acceptance and installation

1. Download to a temporary file on the same filesystem as the accepted bundle,
   with bounded transfer size/time. Keep the current accepted file intact.
2. Verify the outer signature using provisioned keys and allowed algorithms.
   Parse and validate the signed schema, identifier, sequence, publication
   time, resource uniqueness, and issuer/key delegations.
3. Validate every required resource, including signed status lists, identifier
   matching, index/bit-width support, and acceptable keys. Resolve references
   exclusively from this candidate snapshot or deployment-supplied material.
   Bound expanded status-list sizes as well as compressed/file sizes.
4. Construct the complete new in-memory view. Reject incomplete, conflicting,
   invalid, or unsupported candidates without disturbing the previous view.
5. Commit the validated file by atomic rename and switch the in-memory view as
   one accepted snapshot. Use appropriate file/directory synchronization if
   crash durability is required. A restart must be able to rebuild from that
   single accepted file. Extracted local files, if used, are derived caches.

If separate processes need extracted files, stage a complete generation and
switch a generation pointer; do not update their live files individually.
Readers must not combine one generation's trust list with another's status.

Keep rollback high-water information with the accepted deployment snapshot;
it is not visitor data. Reject a lower sequence during normal updates, or
different bytes claiming the same already accepted sequence. Bootstrapping or
deliberately restoring an older deployment requires a defined administrator
procedure, not silent fallback.

## 6. Freshness and indefinite holdover

Propose measuring the normal 73-hour age limit from the signed bundle
publication time, not from the time an HTTP response happened to arrive.
Publish fresh snapshots on the daily schedule. Record successful download
times separately for operational reporting. This prevents repeated delivery
of an old but validly signed file from resetting its age.

Manual holdover deliberately stops applying the snapshot-age limit; it does
not undo revocations in the held snapshot or bypass credential/signature
validity. Never enter it automatically after refresh failure.

The pinned IETF status-list draft requires an explicit Status List JWT `exp`
to be respected when present. For project-controlled lists intended to work
with indefinite holdover, propose omitting that optional (RECOMMENDED) claim
and documenting the availability rationale. Include `iat` and propose
`ttl: 86400` as refresh guidance. Enforce local 73-hour freshness in normal
mode. If a supplied list does contain `exp`, reject it after that deadline;
manual holdover does not turn an expired list into a conforming one.

Similarly, avoid an outer bundle format with a mandatory hard expiry if it
must support the selected holdover behavior. An intrinsic issuer/delegation
or credential expiry is distinct from a snapshot refresh deadline.

## References

- [JWS, RFC 7515](https://www.rfc-editor.org/rfc/rfc7515.html).
- [IETF Token Status List, pinned draft -21](https://github.com/oauth-wg/draft-ietf-oauth-status-list/tree/draft-ietf-oauth-status-list-21).
- [walt.id Verifier API 2, v1.2.0](https://github.com/walt-id/waltid-identity/tree/v1.2.0/waltid-services/waltid-verifier-api2).

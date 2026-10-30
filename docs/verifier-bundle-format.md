# Draft: verifier resource bundle

Status: draft schema. The selected container and signing roles below record
accepted decisions; the precise adapter schema is still to be finalized. This
does not define an implemented endpoint or a new credential format. The
credential profile is in
[credential-profile-and-authorization-policy.md](credential-profile-and-authorization-policy.md).

## 1. Requirements and selected container

Fetch one HTTPS resource, for example
`https://callsignconnect.cloud/verifiers/bundle.jws`, as a single file. The
normal refresh interval is 24 hours. After complete download and validation,
accept the entire snapshot atomically; no request triggered by a credential
presentation resolves additional resources.

The selected container is a **JSON payload inside one compact JWS**.
The payload contains the trust list and all resources directly. Use an existing
JOSE implementation to sign and verify the exact JWS payload bytes. JSON
canonicalization is not needed when verifying those original bytes. This is
a signed data file, not an archive that must be unpacked before validation.

The selected format is **Compact JWS containing JSON and complete embedded
resources**: one signature and one file, without archive paths or extraction
semantics. Base64url adds size overhead, normally acceptable for this bundle.

A detached signature beside the bundle would require a second response unless
both are packaged in a single outer file. HTTPS authentication remains enabled
even when the bundle has its own signature. Do not place secrets or private
keys in this public artifact.

## 2. Signing authority

Provision a set of authorized project certificates independently in the
verifier's local deployment configuration. That locally provisioned set is
the authority for verifying the outer bundle. Accept the compact JWS when its
one signature verifies under any one certificate's authorized public key;
this is not threshold or multi-party signing. A key or certificate delivered
inside an otherwise untrusted candidate bundle cannot authorize that bundle's
own signature or change the locally authorized set.

Use P-256 keys with ES256 for this integration. Keep separate keys for the
bundle, the default issuer's credentials, and its status lists, even when the
project operates all three. A signed issuer entry delegates the recorded
credential or status authority to its listed key and scope; it does not grant
that key bundle-signing authority.

| Signing role | What it proves and authorizes |
| --- | --- |
| Bundle signer | Authenticates the complete resource snapshot and its issuer/key delegations. Its public key is authorized only by the locally provisioned project certificate set. |
| Credential signer | Attests the credential's claims. Its bundle entry grants only the listed credential types and call-sign prefixes. |
| Status-list signer | Authenticates status values for explicitly listed status-list identifiers. Credential-signing authority does not grant this role, or vice versa. |
| Holder key | Proves that the presenting wallet controls the key bound to the credential. It does not authorize credential issuance, status publication, or bundle signing. |

Trust infrastructure, root/intermediate hierarchy, multi-party distribution,
and the provisioning/rotation lifecycle of the local project certificate set
are outside this integration's scope. Do not introduce new certificate-path
validation or root requirements for bundle acceptance. The locally provisioned
authorized certificate keys are sufficient.

The protected JWS header should contain a fixed application type, the approved
algorithm, and a signer identifier such as
`tag:callsignconnect.cloud,2026-10:trustee-key:1`. Treat the identifier as a
lookup into locally provisioned authorized certificate keys, never a network
location or permission to trust an embedded key. Algorithm acceptance is
configured per role; the candidate cannot expand it by choosing a header value.

The candidate bundle cannot authorize a new bundle signer. Managing the local
certificate set is a deployment concern outside this schema. Multiple keys
may be locally authorized at once, but any one valid signature is sufficient.
Issuer credential-key rotation is represented separately in the bundle and
does not change the local bundle-signing authority.

## 3. Trust-list contents

A JSON list records issuers, public keys, and prefixes. Each record also needs
an unambiguous issuer identifier,
key identity/role, credential-type scope, and a list of permitted prefix
expressions. The display name is informational.

Proposed fields:

| Field | Purpose |
| --- | --- |
| Bundle schema identifier | Exact data-format/version contract; reject unsupported schemas. |
| Bundle identifier | Stable tag URI for this stream, separate from its HTTPS download URL. |
| Monotonic sequence | Detect rollback relative to the last accepted snapshot. Re-fetching the same snapshot does not advance it. |
| Signed publication time | Determine snapshot age; downloading old signed bytes again must not make them fresh. |
| Issuer identifier and display name | Match the declared issuer; provide a human-readable label without making the label a trust anchor. |
| Authorized signing keys/certificates | Public material and stable key identity, with distinct credential/status-signing roles and any validity bounds. These are not bundle trust anchors. |
| Credential-type and prefix delegation | Limit which type and call-sign namespace each key can attest. |
| Status-list delegation | Explicitly list the status-list identifiers each status key may sign; no authority is inherited from credential-type or prefix scope. |
| Complete resource map | Type metadata, signed Status List Tokens, and any other material required by validation, indexed by tag identifiers. |

Key rotation requires more than one simultaneously listed key when old
credentials remain valid. Removing or restricting a key changes subsequent
authorization according to the existing snapshot/call policy. Where scope is
attached to a key, another key under the same issuer does not inherit it
implicitly. Validate uniqueness and conflicting delegations when accepting
the bundle, rather than allowing parser order to resolve them.

Use a `prefixes` array containing literal prefixes or the restricted
character-class notation defined in [call-sign-syntax.md](call-sign-syntax.md).
For example, SARTS can use `["9V", "S6"]` and FARA `["3D[N-Z]"]`.
The verifier enforces start-of-string matching, independently of the full
call-sign syntax check. The array supplies alternatives; publishers supply
neither anchors nor unrestricted regex syntax. An empty array grants no
authority. Validate all patterns while accepting a candidate bundle.
There are no call-sign formation or temporary/special classification fields.
No Appendix 42 allocation database is compiled into the application.

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
          "id": "tag:callsignconnect.cloud,2026-10:credential-key:1",
          "jwk": {
            "kty": "EC",
            "crv": "P-256",
            "x": "<credential-public-key-x>",
            "y": "<credential-public-key-y>"
          },
          "uses": ["credential"],
          "credential_types": [
            "tag:callsignconnect.cloud,2026-10:call-sign-attestation:1"
          ],
          "prefixes": ["X1"]
        },
        {
          "id": "tag:callsignconnect.cloud,2026-10:status-key:1",
          "jwk": {
            "kty": "EC",
            "crv": "P-256",
            "x": "<status-public-key-x>",
            "y": "<status-public-key-y>"
          },
          "uses": ["status-list"],
          "status_lists": [
            "tag:callsignconnect.cloud,2026-10:status-list:1"
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

This example uses separate credential and status-list keys. Only the
credential key carries `credential_types` and `prefixes`; the status key's
`status_lists` authorizes exactly the matching resource identifier. Neither
key is a bundle trust anchor. The bundle signer is selected from the separate
locally provisioned project certificate set, not from this payload. Any
additional public verification material and status lists needed by the selected
verifier must be present in the snapshot or local deployment configuration.
The precise local adapter schema is to be finalized against walt.id v1.2.0.

An outer bundle signature authenticates the snapshot and its associations.
The embedded Status List JWT still has its own signature and authorized signer,
whose `status_lists` scope must include that list identifier. Each project
status list uses `status_list.bits: 2`; this width is mandatory for the selected
profile, rather than a configurable choice. Validate the token as required by
the pinned status-list specification. Preserve its
original compact encoding instead of parsing and re-signing it during packing.

## 5. Acceptance and installation

1. Download to a temporary file on the same filesystem as the accepted bundle,
   with bounded transfer size/time. Keep the current accepted file intact.
2. Verify the one outer signature using any one authorized public key from the
   locally provisioned project certificate set and ES256. A candidate's `kid`
   only selects among those local keys; it cannot introduce a key or fetch one.
   Parse and validate the signed schema, identifier, sequence, publication
   time, resource uniqueness, and issuer/key delegations.
3. Validate every required resource, including signed status lists, identifier
   matching, mandatory two-bit status entries, valid indices, and acceptable
   keys with the explicit role and list-ID scope. Resolve references
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
with indefinite holdover, omit that optional (RECOMMENDED) claim; this is the
accepted availability choice for project-controlled lists. Include `iat` and
`ttl: 86400` as refresh guidance. Enforce local 73-hour freshness in normal
mode. If a supplied list does contain `exp`, reject it after that deadline;
manual holdover does not turn an expired list into a conforming one.

Similarly, avoid an outer bundle format with a mandatory hard expiry if it
must support the selected holdover behavior. An intrinsic issuer/delegation
or credential expiry is distinct from a snapshot refresh deadline.

## 7. Remaining schema decisions and proposed v1 defaults

The container, signing algorithms, local bundle-verification certificates,
embedded resources, status width and refresh/holdover model are selected.
The remaining work is to make the trust-list associations and validation
rules precise. The following defaults are proposed, rather than additional
accepted policy decisions:

| Decision | Proposed v1 rule |
| --- | --- |
| What authorizes an issuer key? | The authenticated bundle entry is the delegation. Its public P-256 JWK is authoritative; an optional supplied certificate must contain the same leaf public key and cannot add authority. A separate project certification path is not required for this initial representation. |
| How is a credential bound to that entry? | Exact-match signed credential `iss` to issuer `id`, then match the successfully verified signing public key to that issuer's authorized key. A protected `kid`, when supplied, is a selector within that issuer and must agree with the selected key. Neither issuer name nor `kid` alone grants trust. |
| Who owns a status list? | Add an `issuer` owner to each status resource. Initially require credential `iss`, resource owner and Status List JWT `iss` to agree, and require JWT `sub` to equal resource `id`. Verify the separate status key's explicit `status_lists` scope. Requiring `iss` is an application-profile rule beyond the IETF draft's baseline. Cross-issuer/shared status services would need a later explicit delegation rule. |
| How long does a delegation last? | In the minimal representation a key remains authorized while present in the accepted snapshot; removal/restriction affects subsequent admissions. If an actual delegation has a finite validity period, represent and enforce it explicitly rather than silently extending it through holdover. Finalize the names and requiredness of any such bounds before a dated delegation is used. |
| How are identity, ambiguity and rotation handled? | Unique issuer IDs, unique key IDs within each issuer and unique resource IDs; no conflicting ownership or duplicate JSON object members. Retaining multiple old/new keys and overlapping prefix scopes is allowed for rotation. Credential and status signing keys remain distinct. |

The current abridged example predates the proposed status-resource `issuer`
field. Before treating that example as a usable v1 payload, add the owner
and the corresponding required Status List JWT `iss` and enforce the
cross-resource associations above.

The remaining format mechanics can be chosen during implementation:

- Define required and optional fields in a machine-readable JSON Schema and
  reject unknown fields for that schema version. Use public-only P-256 JWKs;
  reject private key parameters and role-inappropriate fields.
- Require the expected schema and bundle-stream identifiers, a nonnegative
  integer sequence and an integer publication timestamp. Reject future
  publication, rollback and changed bytes claiming an accepted sequence.
  An exact retry of the accepted bytes is harmless and does not refresh age.
- Require type metadata `vct` to equal its resource ID, status JWT `sub` to
  equal its resource ID, and every required reference to resolve locally.
  Validate these relationships in code as well as JSON field shapes.
- Set explicit file, decompression, field-length and entry-count limits;
  specify certificate/resource encodings and reject missing or duplicate
  resources. These are parser and deployment bounds, not another trust model.

Once these associations are agreed, the JSON Schema plus semantic validator
can make the format usable without specifying the future trustee PKI or
waiting for support for additional wallets.

## References

- [JWS, RFC 7515](https://www.rfc-editor.org/rfc/rfc7515.html).
- [IETF Token Status List, pinned draft -21](https://github.com/oauth-wg/draft-ietf-oauth-status-list/tree/draft-ietf-oauth-status-list-21).
- [walt.id Verifier API 2, v1.2.0](https://github.com/walt-id/waltid-identity/tree/v1.2.0/waltid-services/waltid-verifier-api2).

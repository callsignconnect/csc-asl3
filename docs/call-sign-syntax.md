# Draft: call-sign syntax and issuer prefix validation

The verifier performs two independent boolean checks: the complete call sign
has an accepted syntax and length, and it begins with a prefix authorized for
the verified issuer/key. It does not extract or retain a call-sign type,
nationality-identification structure, or ordinary/special classification.

The syntax is based on ITU Radio Regulations 2024 Volume 1, Nos. 19.50, 19.68,
19.68.1, 19.68A, and 19.69. The primary text consulted is reproduced in the
[pinned mirror](https://github.com/Zakaria010/Radio-RAG/blob/c944a90ec847378bae5fa09425ee4c2ef99508de/data/2400594-RR-Vol%201-E-A5.pdf),
printed pages 269 and 271. The original publication is the
[ITU Radio Regulations, 2024](https://www.itu.int/pub/R-REG-RR-2024).
The mirror's LFS content SHA-256 is
`a19db60201342f44443143c01c528abe725b93cf133602631edaa2b6c9ba6a8f`.
Its bytes were not independently compared with the currently hosted ITU file.

## 1. Whole-call-sign validation

The accepted expression is:

```regex
(?![0-9]{2})(?:[BFGIKMNRW]|[A-Z0-9]{2,3})[0-9][A-Z0-9]*[A-Z]
```

Apply it as a full-string match. Check the application's maximum length of
**63 characters** separately, before matching. The expression admits only
uppercase ASCII letters and digits, so a valid claim's character count equals
its byte count and fits a single DNS label. This is an application limit, not
an asserted ITU or SIP limit.

- The negative lookahead enforces No. 19.50's prohibition on two initial digits.
- `[BFGIKMNRW]` is the one-character set explicitly specified by No. 19.68,
  not an Appendix 42 allocation lookup.
- `{2,3}` accommodates the other identification lengths, including half series.
- `[0-9]` includes 0 and 1 as permitted for amateur stations by No. 19.69.
- The final character must be a letter.

Ordinary/special and half-series suffix-length distinctions are intentionally
not enforced. Those assignment decisions belong to the administration and
are faithfully preserved by the issuer. There are no separate temporary-use
flags or formation grants in the verifier's trust data. The shared expression
is the project's combined syntax envelope; it does not purport to check every
regulatory obligation or grant legal operating rights.

Python illustration, not an implementation in the application:

```python
import re

CALL_SIGN_RE = re.compile(
    r"(?![0-9]{2})(?:[BFGIKMNRW]|[A-Z0-9]{2,3})[0-9][A-Z0-9]*[A-Z]"
)

def valid_call_sign(call_sign):
    return (
        isinstance(call_sign, str)
        and 1 <= len(call_sign) <= 63
        and CALL_SIGN_RE.fullmatch(call_sign) is not None
    )
```

Use ASCII classes, not `\w` or `\d`. Do not case-fold, trim, or otherwise repair
a malformed signed claim. Full matching also rejects a trailing newline.
Portable prefixes/suffixes and slash-qualified operating labels are excluded.

## 2. Issuer-authorized prefixes

The trust list supplies a `prefixes` array for each authorized issuer/key.
At least one entry must match at the **beginning** of the already validated
call sign. No match, or an empty array, means no authority. Do not search
elsewhere in the call sign or require the prefix to match the entire value.

Recommended representations for the examples discussed:

```json
{"prefixes": ["9V", "S6"]}
```

```json
{"prefixes": ["3D[N-Z]"]}
```

The first is equivalent to the intended prefix alternatives `(9V|S6)`;
separate array entries provide the alternatives without requiring regex
alternation. The second compactly represents the indicated range.

The verifier enforces prefix semantics; the publisher does not supply anchors.
Use Python 3.15's `Pattern.prefixmatch(call_sign)` to state that operation
explicitly; it starts at position zero and needs no `^`. An explicit
compiler-generated anchor can also make the contract visible:

```python
# Python 3.15 or later.
# validated_pattern has already passed the restricted-language parser below.
prefix_re = re.compile(r"\A(?:" + validated_pattern + r")")
permitted = valid_call_sign(call_sign) and prefix_re.prefixmatch(call_sign) is not None
```

`prefixmatch` was added in Python 3.15; `match` is its older, soft-deprecated
name, with no scheduled removal. The implementation on ASL3/Debian 13 will
use the older `Pattern.match(call_sign)` spelling with exactly the same
prefix semantics, because its Python predates 3.15. Keep `prefixmatch` in
this illustration; no application runtime upgrade is required.

This code does not implement pattern validation. Never pass arbitrary trust-list
text straight to a general regex compiler. If alternatives were ever introduced,
`^9V|S6` would not anchor both branches when used with a search API; grouping
inside the verifier-generated anchor avoids that ambiguity.

### Proposed restricted pattern language

Allow only uppercase ASCII letter/digit literals and positive character
classes containing those characters or ranges within them, such as `[N-Z]`
or `[0-3]`. Each pattern and class must be nonempty. Ranges must ascend and stay
entirely within `A-Z` or entirely within `0-9`; reject `[0-Z]`, which crosses
punctuation in ASCII.

Do not permit groups, alternation, anchors, wildcards, quantifiers, escapes,
negated classes, lookarounds, backreferences, or caller-supplied flags. The
array supplies OR semantics. Parse and validate the restricted notation before
compiling, and reject a candidate bundle containing an invalid pattern rather
than skipping it or treating it as unrestricted. Each pattern consumes at least
one and at most 63 call-sign characters; impose appropriate encoded-size and
entry-count bounds on the bundle as well.

There is no captured structural prefix to reconcile with the issuer's prefix
expression: these are independent boolean checks. The project trustee delegates the
namespace through signed trust data; no Appendix 42 allocation table or
special-case test-prefix bypass is built into the code.

## 3. Examples

| Value/check | Result |
| --- | --- |
| `W1AW`, `M0ABC`, `9M2ABC`, `A65AB`, `3DA0ABC`, `AB12C` | Accepted syntax; issuer prefix permission still required. |
| `W1ABCDE`, `AX2020STAYHOME` | Accepted extended syntax without a separate special-call flag. |
| `X10CSC` with issuer prefix `X1` | Accepted syntax and prefix check. |
| `3DN0ABC` with issuer prefix `3D[N-Z]` | Accepted syntax and prefix check. |
| `3DA0ABC` with issuer prefix `3D[N-Z]` | Valid syntax but outside that issuer's prefix authority. |
| `G9V1XX` with issuer prefixes `9V` and `S6` | Valid syntax but neither prefix occurs at the beginning. |
| `120A`, `11A`, `W1`, `W1ABC1`, `W1A/P`, lowercase, trailing whitespace/newline | Rejected syntax. |
| Syntactically matching value with 64 characters | Rejected by the separate application length rule. |
| `X1CSC` | Rejected: neither the one-character nor the two/three-character branch supplies the required digit position. |

Use `X10CSC` for the corrected synthetic example, retaining the unallocated
`X1` namespace. The prototype's old placeholder identity is application code
to replace when implementing verifier authentication; this document does not
change that code.

## References

- [Python 3.15 prefix matching](https://docs.python.org/3.15/library/re.html#re.prefixmatch).

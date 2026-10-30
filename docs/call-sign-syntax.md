# Draft: call-sign syntax and delegated prefix validation

These expressions implement the formation shapes in ITU Radio Regulations
2024 Volume 1, Nos. 19.50, 19.68, 19.68.1, 19.68A, and 19.69. They do not
contain Appendix 42 allocations and are not, by themselves, issuer
authorization checks.

The primary text consulted is the ITU PDF reproduced in the
[pinned mirror](https://github.com/Zakaria010/Radio-RAG/blob/c944a90ec847378bae5fa09425ee4c2ef99508de/data/2400594-RR-Vol%201-E-A5.pdf),
printed pages 269 and 271. The original publication is the
[ITU Radio Regulations, 2024](https://www.itu.int/pub/R-REG-RR-2024).
The mirror's LFS content SHA-256 is
`a19db60201342f44443143c01c528abe725b93cf133602631edaa2b6c9ba6a8f`.
Its bytes were not independently compared with the currently hosted ITU file.

## 1. Ordinary formation shapes

Use ASCII character classes and Python `re.fullmatch`; do not use `\w`, `\d`,
case folding, trimming, or an end anchor that accepts a trailing newline for
the signed claim. Under No. 19.69, 0 and 1 are allowed for amateur stations.

| Form | Full-match expression |
| --- | --- |
| One-character identification, No. 19.68 | `[BFGIKMNRW][0-9][A-Z0-9]{0,3}[A-Z]` |
| Two-character identification, Nos. 19.50/19.68 | `(?:[A-Z][A-Z0-9]|[0-9][A-Z])[0-9][A-Z0-9]{0,3}[A-Z]` |
| Three-character half-series identification, No. 19.68.1 | `(?:[A-Z][A-Z0-9]|[0-9][A-Z])[A-Z0-9][0-9][A-Z0-9]{0,2}[A-Z]` |

The first form has a suffix of one through four characters, ending in a
letter. The second has the same suffix constraint and a two-character prefix
whose first two characters cannot both be digits. The half-series form has
three identification characters and a suffix of one through three characters,
ending in a letter. Its use requires the corresponding half-series authority;
matching that expression alone does not establish it.

The literal `[BFGIKMNRW]` comes from No. 19.68 itself. It is a formation rule,
not an embedded lookup of currently allocated Appendix 42 series.

## 2. Temporary extended suffixes

No. 19.68A permits administrations to authorize more than four suffix
characters for temporary special occasions. Add separate, explicitly
authorized forms:

```text
[BFGIKMNRW][0-9][A-Z0-9]{4,}[A-Z]
(?:[A-Z][A-Z0-9]|[0-9][A-Z])[0-9][A-Z0-9]{4,}[A-Z]
```

These require at least five suffix characters and retain the final-letter
condition. Do not grant them by default merely because the expression matches.
The text does not explicitly relax the separate three-character suffix cap
in No. 19.68.1; extending that form needs a justified interpretation and
administrative authority, not a silent regex change.

The provision supplies no upper length limit for those special suffixes. A
documented application input-size limit still needs to be selected for the
HTTP/SIP implementation; it should not be misrepresented as an ITU limit.

## 3. Capture and authorize all possible parses

Use separate patterns so prefix, digit, and suffix remain available to the
trust-policy evaluator:

```python
import re

PREFIX2 = r"(?:[A-Z][A-Z0-9]|[0-9][A-Z])"
FORMS = {
    "one-character": re.compile(
        r"(?P<prefix>[BFGIKMNRW])(?P<digit>[0-9])"
        r"(?P<suffix>[A-Z0-9]{0,3}[A-Z])"
    ),
    "two-character": re.compile(
        rf"(?P<prefix>{PREFIX2})(?P<digit>[0-9])"
        r"(?P<suffix>[A-Z0-9]{0,3}[A-Z])"
    ),
    "half-series": re.compile(
        rf"(?P<prefix>{PREFIX2}[A-Z0-9])(?P<digit>[0-9])"
        r"(?P<suffix>[A-Z0-9]{0,2}[A-Z])"
    ),
    "temporary-one-character": re.compile(
        r"(?P<prefix>[BFGIKMNRW])(?P<digit>[0-9])"
        r"(?P<suffix>[A-Z0-9]{4,}[A-Z])"
    ),
    "temporary-two-character": re.compile(
        rf"(?P<prefix>{PREFIX2})(?P<digit>[0-9])"
        r"(?P<suffix>[A-Z0-9]{4,}[A-Z])"
    ),
}

def candidate_forms(call_sign):
    return [
        {"formation": name, **match.groupdict()}
        for name, pattern in FORMS.items()
        if (match := pattern.fullmatch(call_sign)) is not None
    ]
```

Authorize a candidate only if the verified issuer/key's trust-list delegation
permits that identification prefix and formation, including any temporary
extension. For example, `AB12C` admits both `AB + 1 + 2C` and `AB1 + 2 + C`.
Do not pick the first or greediest parse and infer its authority. At least one
candidate must satisfy the explicit delegation; no candidate means rejection.

The illustrative bundle uses a base `formation` plus a
`temporary_extended_suffix` flag. Map a candidate such as
`temporary-two-character` to base formation `two-character` and additionally
require that flag to be true; ordinary candidates do not require it. Do not
compare those differently represented names literally and accidentally skip
the extension permission check.

Any additional prohibitions beyond the cited formation rules need their own
documented rule. These expressions do not claim to encode every regulatory
obligation or confer legal operating rights.

## 4. Examples and the existing prototype identity

| Value | Shape result |
| --- | --- |
| `W1AW`, `M0ABC` | Ordinary one-character form. |
| `9M2ABC`, `A65AB`, `X10CSC` | Ordinary two-character form; prefix authority is still required. |
| `3DA0ABC` | Half-series form, requiring the applicable delegated authority. |
| `AB12C` | Multiple ordinary parses; check the issuer's permitted form/prefix. |
| `W1ABCD` | Four-character suffix permitted by the ordinary form. |
| `W1ABCDE` | Requires the explicitly authorized temporary extended form. |
| `W1`, `W1ABC1`, `11A`, `W1A/P`, lowercase, trailing whitespace/newline | Reject under these shapes. |
| `X1CSC` | Reject: `X` is not a permitted one-character identification, and `X1` is not followed by the required digit. |

The previous documentation's `X1CSC` example was not consistent with the literal
formation rules. Use `X10CSC` as the proposed correction: it retains the
unallocated `X1` test namespace, then digit `0`, then suffix `CSC`. No production
allocation check or test-only parser exception is needed. The prototype's
current placeholder identity remains application code to replace when
implementing verifier authentication; this document does not change that code.

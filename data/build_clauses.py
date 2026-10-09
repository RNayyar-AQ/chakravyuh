"""Split Indian gazette Acts (pdftotext -layout-less output) into section-level clause records.

Usage: python3 -I build_clauses.py <pdf> <instrument_id> <instrument_name> <source_url> <out.jsonl>
Each record: clause_id, instrument, section, heading-free verbatim text, page, sha256, source_pdf_sha256.

SCOPE, AND WHY IT HAS NOT BEEN WIDENED
  This splitter handles ACTS: top-level sections numbered `1.`, `2.`, ... and it has been run on
  exactly two, producing 62 sections for the Telecommunications Act 2023 and 44 for the DPDP Act
  2023 -- both counts matching the Acts.

  The showcase runbook asks to adapt the regex for Rules (`^\d+\.` rule numbers) and SOPs
  (numbered headings like `5.2.16`). That has deliberately NOT been done, because we hold no
  Rules or SOP PDF to run it against. A splitter written for a document format nobody has seen
  is untested code that will be trusted the first time it is used on a real gazette, which is
  precisely when a silent mis-split becomes a fabricated clause.

  The `expected` counter below is the reason to trust the two runs that did happen: a section
  header only opens a new record when its number is the next one in sequence, so a page-number
  or a cross-reference that looks like a header cannot start a record, and a dropped section
  would show up immediately as a short count.

  When the Suspension Rules 2024, the Telecom Cyber Security Rules 2024 and DoT SOP-2020 are in
  `data/sources/IN/`, widen `SEC` then -- and check the resulting count against the instrument,
  the way these two were checked.
"""
import hashlib, json, re, subprocess, sys

pdf, iid, name, url, out = sys.argv[1:6]
pdf_sha = hashlib.sha256(open(pdf, "rb").read()).hexdigest()
pages = subprocess.run(["pdftotext", "-q", pdf, "-"], capture_output=True, text=True).stdout.split("\f")

# Drop running heads and page furniture
JUNK = re.compile(r"^(THE GAZETTE OF INDIA EXTRAORDINARY|\[PART II|SEC\. 1\]|_+|\d{1,3})$")
lines = []
for pno, page in enumerate(pages, 1):
    for ln in page.splitlines():
        s = ln.strip()
        if s and not JUNK.match(s):
            lines.append((pno, s))

SEC = re.compile(r"^(\d{1,3})\.\s*(\(1\)|[A-Z“\"(])")
records, cur = [], None
expected = 1
for pno, s in lines:
    m = SEC.match(s)
    if m and int(m.group(1)) == expected:
        if cur:
            records.append(cur)
        cur = {"section": m.group(1), "page": pno, "text": [s]}
        expected += 1
    elif cur:
        cur["text"].append(s)
if cur:
    records.append(cur)

with open(out, "w") as f:
    for r in records:
        text = " ".join(" ".join(r["text"]).split())
        f.write(json.dumps({
            "clause_id": f"{iid}.s{r['section']}",
            "instrument": name,
            "jurisdiction": "IN",
            "section": r["section"],
            "page": r["page"],
            "text_verbatim": text,
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "source_url": url,
            "source_pdf_sha256": pdf_sha,
        }, ensure_ascii=False) + "\n")
print(f"{name}: {len(records)} sections -> {out}")

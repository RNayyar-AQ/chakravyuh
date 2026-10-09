"""Split Indian gazette Acts (pdftotext -layout-less output) into section-level clause records."""
import hashlib, json, re, subprocess, sys

pdf, iid, name, url, out = sys.argv[1:6]
pdf_sha = hashlib.sha256(open(pdf, "rb").read()).hexdigest()
pages = subprocess.run(["pdftotext", "-q", pdf, "-"], capture_output=True, text=True).stdout.split("\f")

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

# C04: RDSO / railway approved vendors (rdso.indianrailways.gov.in, IREPS UVAM)

**Status:** ⛔ BLOCKED for vendor names: the directory needs a human sign-in (mobile number, image code, OTP). The tool for a
manual pull is ready. RDSO's open item lists (133 items) are built, but 0 / 2 items are done: two proxies were refused, and the site answers again now.
**Updated:** 2 Nov 2026 10:32 CET · **Family:** `contractor-registration` · **Code:** `s1d-labs/contractor-registration@685c82a` (`main`);
`tools/ireps_vendors.py` on `proxy-check-nhai-refetch` @ `5d02ff5` (PR #7, open)
**Projects:** `contractor-registration-rdso-items` (adapter `rdso`, target `rdso.indianrailways.gov.in`, `proxy="IN"`, 1 worker)
**Data:** `select … from public.records where project = 'contractor-registration-rdso-items'` (empty so far)
**Previous report:** first report

---

## Contents
1. [TL;DR](#1-tldr) · 2. [Where things stand](#2-where-things-stand) · 3. [Pick up here](#3-pick-up-here) · 4. [What stands out](#4-what-stands-out)
· 5. [The source](#5-the-source) · 6. [How it is collected](#6-how-it-is-collected) · 7. [The data](#7-the-data) · 8. [Verification](#8-verification)
· 9. [Known gaps and quality issues](#9-known-gaps-and-quality-issues) · 10. [Risks and open decisions](#10-risks-and-open-decisions) · 11. [Next steps](#11-next-steps)

---

## 1. TL;DR
- **The vendor directory is on IREPS UVAM**, open to guests who sign in with an Indian mobile number, an image verification code and
  an OTP. No account is needed, but a person must do each sign-in.
- **`tools/ireps_vendors.py login`** (PR #7) does that sign-in with the person at the keyboard, keeps the session on the box (private
  file) and saves the first directory pages. The export can be written once those pages have been seen.
- **RDSO's own lists:** 25 items with fewer than 3 approved sources, 107 with fewer than 5, and 1 with no Indian source (as on 03.06.2024).
  Tested end to end: 133 records. In the pool both items failed on proxies `95.134.119.238` / `.254`, which answer RDSO again today. The hub retries them.
- **Next:** someone with a phone runs the sign-in once (about 2 minutes); see [3](#3-pick-up-here).

## 2. Where things stand

| Project | State | Items done / total | Failed · pending · running | Records stored | Pace (24 h) | ETA |
|---|---|---:|---|---:|---:|---|
| `-rdso-items` | ⚠️ STALLED | 0 / 2 | 2 · 0 · 0 | 0 | 0 | next retry; 133 records expected |
| IREPS vendor directory | ⛔ BLOCKED | — | — | — | — | after a human sign-in |

- Runs: 2, both finished with 0 records (2 Nov 09:07 and 09:49 CET), with 4 and 2 connection errors. The items have 3 tries each of 40.

## 3. Pick up here
- **Repo:** `~/contractor-registration` · **Try the item lists:** `myproxy run ~/.venvs/cr/bin/python crawl.py --local rdso '{"section": "0,5,6634"}'`
- **IREPS sign-in (needs the phone that gets the OTP), once PR #7 is merged:**
  ```
  cd ~/contractor-registration && git pull
  ~/.venvs/cr/bin/python tools/ireps_vendors.py login
  ```
  It asks for the mobile number, prints the path of the verification image (open it in VS Code), asks for the code, sends the
  OTP, and asks for the OTP (not shown). The landing page goes to `~/ireps-export/<date>/landing.html`. Tell Claude when it's
  there, so the export can be written while the session lasts.
- **Waiting on:** trideep (merge PR #7, do the sign-in, check the IREPS terms of use).

## 4. What stands out
1. **No Indian vendor for some catenary and radio items.** In the lists, sub-items such as the *Spring Auto tensioning device for
   2400 kgf (OHE)* and the *25 W VHF digital radio set* have **0** approved vendors. The *continuous cast copper wire rod, 22.5–26 mm*
   has one foreign source and no Indian one.
2. **The open count report closed.** The anonymous item/vendor count report (`itemVendorCountReport.do`) now redirects to the
   sign-in too, so even counts per directorate need a session.
3. **The planned-sources page counts 55 "India-only" hosts here.** RDSO and IREPS answer the hub's Indian proxies, though not every proxy every time.

## 5. The source
- **RDSO** (`rdso.indianrailways.gov.in`): a JSP CMS. Page `view_section.jsp?id=0,5,6634` links 3 PDFs (Word tables).
- **IREPS UVAM** (`ireps.gov.in/epsn/cvap/...`): Struts. The guest sign-in form is `guestLogonForm` → `/epsn/guestLogin.do`. The image
  code comes from `POST /epsn/generateCaptchaAction.do` (JSON: base64 PNG plus a token). The OTP request is `activity=submitGetOTP`
  (answers `OK#…`), and the sign-in is `activity=submitOTP`. Mobile numbers outside +91 must use the IREPS app.

### 5.1 Site map

| What | URL | Notes |
|---|---|---|
| Items with few sources | `rdso.indianrailways.gov.in/view_section.jsp?lang=0&id=0,5,6634` | 3 PDFs, open |
| Vendor directory | `ireps.gov.in/epsn/cvap/admintab/vndrDirectoryAnon.do?activity=displayFirst&approvAgencyCode=-2` | **guest sign-in: mobile + image code + OTP** |
| Item master | `ireps.gov.in/epsn/cvap/admintab/viewItemMasterAnon.do` | same sign-in |
| Item / vendor counts | `itemVendorCountReport.do` | now redirects to the sign-in |

## 6. How it is collected
- **Item lists:** `adapters/rdso.py` reads the page, then each PDF about sources. Words are read with positions (`statepwd.page_words`).
  Column borders lie half way between caption cells, and justified descriptions are read across their id column.
- **Vendor directory:** `tools/ireps_vendors.py` (box only, never in the pool). `login` and `fetch` are written; `export` comes
  after the pages are mapped. One request every 2 s. The mobile number and OTP are sent only to IREPS. The session cookies stay in
  `~/.cache/s1d/ireps-session.json` (mode 600). Output is uploaded with `mybucket sync ~/ireps-export ireps-uvam`.
- **Decision (trideep, 2 Nov 2026):** vendor names by a manual monthly pull, with a person signing in. The image code and OTP are
  never automated.

## 7. The data
- Item lists (once stored): record `<list>-<item id>-<sub-item id or 0>`. Fields: `list` (`fewer-than-three-sources`,
  `fewer-than-five-sources`, `no-indigenous-source`), `group`, `department`, `directorate`, `item_id`, `item`, `subitem_id`, `subitem`,
  `vendor_count`, `list_as_on`.

```sql
select data->>'list', data->>'item_id', data->>'item', data->>'subitem', data->>'vendor_count' from public.records
where project = 'contractor-registration-rdso-items' order by (data->>'vendor_count')::int, data->>'item_id';
```

## 8. Verification
- Tests: 42 passed, including the "fewer than three" PDF (25 rows) and the page's links. scrape-check through a proxy (1 Nov): 133
  records, same ids on rerun. Row counts equal each list's stated count (25, 107, 1).
- IREPS: the sign-in form, its token and the image code were fetched through a proxy (2 Nov). **The OTP step and the directory pages
  have not been seen.**

## 9. Known gaps and quality issues

| # | Issue | Size | Impact / what to do |
|---|---|---:|---|
| 1 | **Vendor names behind the IREPS sign-in** (at the source) | the whole directory | Manual pull ([3](#3-pick-up-here)). |
| 2 | Item lists not stored yet (missed by us, for now) | 133 items | The hub retries; PR #7 gives back refused proxies. |
| 3 | Lists are from 03.06.2024 (at the source) | 3 PDFs | Checked monthly for new files. |

## 10. Risks and open decisions
- **Risks:** an IREPS session is tied to the address it was opened from. ireps.gov.in answers the team box directly (2 Nov), so
  the whole pull runs from the box without a proxy. IREPS limits OTPs per number ("Maximum OTP limit exceeded").
- **To decide (trideep):** whether the IREPS terms allow storing the directory, and who signs in each month.

## 11. Next steps
**To do now:** 1. Merge PR #7. 2. Run `tools/ireps_vendors.py login` once with the phone. 3. Then Claude maps the pages and writes `export`.
**Later:** 4. Join vendor names to RDSO items and to the other registers.
**Housekeeping:** delete `~/ireps-export` after uploading it to the bucket.

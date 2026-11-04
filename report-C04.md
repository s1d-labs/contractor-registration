# C04: RDSO / railway approved vendors (rdso.indianrailways.gov.in, IREPS UVAM)

**Status:** 💤 PARKED for vendor names: **the IREPS sign-in is on hold until trideep can do it (decided 3 Nov 2026)**. The
directory needs a human sign-in (mobile number, image code, OTP); the tool for that pull is ready on `main`. RDSO's open item
lists (133 items) still fail in the pool: pool runs get connection errors through every proxy, while the same proxy answers from a
team box. PR #9 also sends the project to the hub's India servers.
**Updated:** 4 Nov 2026 09:55 CET · **Family:** `contractor-registration` · **Code:** `s1d-labs/contractor-registration@51547a2` (`main`);
`geo="IN"` on branch `c02-uttarakhand-odisha` (PR #9, open)
**Projects:** `contractor-registration-rdso-items` (adapter `rdso`, target `rdso.indianrailways.gov.in`, `proxy="IN"`, + `geo="IN"` after PR #9, 1 worker)
**Data:** `select … from public.records where project = 'contractor-registration-rdso-items'` (empty so far)
**Previous report:** 2 Nov 2026 10:32 CET

---

## Contents
1. [TL;DR](#1-tldr) · 2. [Where things stand](#2-where-things-stand) · 3. [Pick up here](#3-pick-up-here) · 4. [What stands out](#4-what-stands-out)
· 5. [The source](#5-the-source) · 6. [How it is collected](#6-how-it-is-collected) · 7. [The data](#7-the-data) · 8. [Verification](#8-verification)
· 9. [Known gaps and quality issues](#9-known-gaps-and-quality-issues) · 10. [Risks and open decisions](#10-risks-and-open-decisions) · 11. [Next steps](#11-next-steps)

---

## 1. TL;DR
- **The vendor directory is on IREPS UVAM**, open to guests who sign in with an Indian mobile number, an image verification code and
  an OTP. No account is needed, but a person must do each sign-in.
- **`tools/ireps_vendors.py login`** (on `main`) does that sign-in with the person at the keyboard, keeps the session on the box (private
  file) and saves the first directory pages. The export can be written once those pages have been seen.
- **RDSO's own lists:** 25 items with fewer than 3 approved sources, 107 with fewer than 5, and 1 with no Indian source (as on 03.06.2024).
  Tested end to end: 133 records (again on 4 Nov, through `91.124.42.191` from the box). In the pool, 4 Nov 08:58–09:37 CET, runs
  through all 10 proxies gave connection errors and gave the proxy back without claiming (the items keep their tries).
- **Next:** merge PR #9 (India servers as a second route); the IREPS sign-in stays on hold.

## 2. Where things stand

| Project | State | Items done / total | Failed · pending · running | Records stored | Pace (24 h) | ETA |
|---|---|---:|---|---:|---:|---|
| `-rdso-items` | ⚠️ STALLED | 0 / 2 | 0 · 2 · 0 | 0 | 0 | after PR #9 (India servers); 133 records expected |
| IREPS vendor directory | 💤 PARKED | — | — | — | — | **on hold**: after trideep's sign-in (not scheduled) |

- Runs on 2 Nov (12, through `95.134.119.x`, `91.124.42.193`, `191.219.20.x`) finished with 0 records ("site did not answer"); the
  items have 15 tries each of 40. Since 4 Nov a run checks the site first: 2 runs, 32 connection errors, 16 proxies given back.
- The same item, through the same proxy (`91.124.42.191`), passes scrape-check from the team box (09:22 CET), so the site answers.

## 3. Pick up here
- **Repo:** `~/contractor-registration` · **Try the item lists:** `myproxy run ~/.venvs/cr/bin/python crawl.py --local rdso '{"section": "0,5,6634"}'`
- **🚩 ON HOLD (3 Nov 2026): trideep will do the sign-in later.** When it's time (needs the phone that gets the OTP):
  ```
  cd ~/contractor-registration && git pull
  ~/.venvs/cr/bin/python tools/ireps_vendors.py login
  ```
  It asks for the mobile number, prints the path of the verification image (open it in VS Code), asks for the code, sends the
  OTP, and asks for the OTP (not shown). The landing page goes to `~/ireps-export/<date>/landing.html`. Tell Claude when it's
  there, so the export can be written while the session lasts.
- **Waiting on:** trideep (the sign-in, on hold; check the IREPS terms of use first).

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
| 2 | **Item lists not stored yet** (missed by us, for now) | 133 items | Pool runs can't reach RDSO through the proxies; PR #9 adds the India servers. If those fail too, ask Sarthak to look at the runners' proxy path. |
| 3 | Lists are from 03.06.2024 (at the source) | 3 PDFs | Checked monthly for new files. |

## 10. Risks and open decisions
- **Risks:** an IREPS session is tied to the address it was opened from. ireps.gov.in answers the team box directly (2 Nov), so
  the whole pull runs from the box without a proxy. IREPS limits OTPs per number ("Maximum OTP limit exceeded").
- **To decide (trideep):** whether the IREPS terms allow storing the directory, and who signs in each month.

## 11. Next steps
**To do now:** merge PR #9 and run setup; check `-rdso-items` an hour later.
**On hold (trideep):** 1. Run `tools/ireps_vendors.py login` once with the phone. 2. Then Claude maps the pages and writes `export`.
**Later:** 3. Join vendor names to RDSO items and to the other registers.
**Housekeeping:** delete `~/ireps-export` after uploading it to the bucket.

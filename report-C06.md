# C06: PMGSY (OMMAS) contractor master and works awarded (pmgsy.dord.gov.in)

**Status:** ✅ COMPLETE. **59,843** contractors of all 37 states and **205,987** works awarded (plus 1,200 awarded then terminated)
are stored. Both refresh monthly. The public reports never name the contractor of a work.
**Updated:** 2 Nov 2026 10:32 CET · **Family:** `contractor-registration` · **Code:** `s1d-labs/contractor-registration@685c82a` (`main`);
`awarded_is_package_total` on `proxy-check-nhai-refetch` @ `5d02ff5` (PR #7, open)
**Projects:** `contractor-registration-pmgsy-contractors`, `contractor-registration-pmgsy-agreements` (adapter `pmgsy`, target
`pmgsy.dord.gov.in`, `proxy="IN"`, 2 workers each)
**Data:** `select … from public.records where project = 'contractor-registration-pmgsy-contractors'` / `'…-pmgsy-agreements'` ·
bucket `…/docs/contractor-information/`, `…/docs/agreements/` (the site's CSV exports)
**Previous report:** first report

---

## Contents
1. [TL;DR](#1-tldr) · 2. [Where things stand](#2-where-things-stand) · 3. [Pick up here](#3-pick-up-here) · 4. [What stands out](#4-what-stands-out)
· 5. [The source](#5-the-source) · 6. [How it is collected](#6-how-it-is-collected) · 7. [The data](#7-the-data) · 8. [Verification](#8-verification)
· 9. [Known gaps and quality issues](#9-known-gaps-and-quality-issues) · 10. [Risks and open decisions](#10-risks-and-open-decisions) · 11. [Next steps](#11-next-steps)

---

## 1. TL;DR
- **Contractor master:** 59,843 contractors: 59,319 active, 329 inactive, 164 expired, **31 blacklisted**. Each record has firm, contact,
  state registration number, address, phones, e-mail and PAN (masked by the site), and 56,988 have a PAN.
- **Works awarded:** 205,987 road and bridge works in **125,058 packages**, with sanction year, lengths, sanctioned cost and
  awarded cost. Another 1,200 works were awarded and then terminated.
- **Money:** ₹4.14 lakh crore sanctioned against ₹4.98 lakh crore awarded, counting each package once (ratio 1.20). Counting per work
  would wrongly give ₹7.96 lakh crore, because **24,629 packages repeat the package's amount on every work**. Those rows are now marked.
- **No contractor ↔ work link** in the public reports. Only the officials' OMMAS has it. pmgsytenders.gov.in (GePNIC) may give the
  winner per tender.
- The planned source named omms.nic.in, which is dead; the reports moved to **pmgsy.dord.gov.in**.

## 2. Where things stand

| Project | State | Items done / total | Failed · pending · running | Records stored | Pace (24 h) | ETA |
|---|---|---:|---|---:|---:|---|
| `-pmgsy-contractors` | ✅ COMPLETE | 296 / 296 | 0 · 0 · 0 | 59,843 | 296 | monthly refresh |
| `-pmgsy-agreements` | ✅ COMPLETE | 74 / 74 | 0 · 0 · 0 | 207,187 | 74 | monthly refresh |

- Works were read on 2 Nov, 09:03–10:11 CET, through 2 proxies, with 0 errors. Uttar Pradesh took one CSV of 21k works (~30 s).

| State | Works awarded | Awarded (₹ crore, per package) | | State | Works terminated |
|---|---:|---:|---|---|---:|
| Madhya Pradesh | 23,206 | 40,329 | | Madhya Pradesh | 282 |
| Uttar Pradesh | 21,136 | 65,317 | | Odisha | 123 |
| Bihar | 20,765 | 63,529 | | Assam | 115 |
| Rajasthan | 19,411 | 21,660 | | Chhattisgarh | 97 |
| Odisha | 18,611 | 35,882 | | Tripura | 87 |

## 3. Pick up here
- **Repo:** `~/contractor-registration` · **Run tests:** `~/.venvs/cr/bin/python -m pytest -q tests` · **Try one state:**
  `myproxy run ~/.venvs/cr/bin/python crawl.py --local pmgsy '{"report": "agreements", "state": 30, "state_name": "Sikkim"}'`
- **Next action:** merge PR #7. The next monthly refresh then writes `awarded_is_package_total`; until then, use the SQL in [7](#7-the-data).
- **Waiting on:** nothing.

## 4. What stands out
1. **Awarded cost is per package in some states and per work in others.** Chhattisgarh package `CG1639` shows ₹5,111.40 lakh on
   each of its 5 roads (sanctioned ₹123–619 lakh each), while Sikkim gives each bridge its own amount. *Fix:* the
   `awarded_is_package_total` flag (PR #7); sums take that amount once per package.
2. **Even per package, some states award far above sanction.** The ratio is 2.97 in Tripura, 1.96 in Uttar Pradesh and 1.88 in
   Jharkhand, against 1.20 nationally. *Probably* the agreement includes the five-year maintenance and the state's share, which the
   sanction does not. Not confirmed.
3. **Blacklisting is rare and local.** 31 blacklisted contractors in all of India: 15 in Assam, 13 in Jharkhand, 2 in Arunachal
   Pradesh and 1 in Uttarakhand. Madhya Pradesh (6,169 contractors) and Bihar (5,553) list none.
4. **One package, two bridges with one name.** In Sikkim, package `SK03P7P11R` has two 20 m bridges both called *Ramitey Khola*,
   with different costs, so work ids include cost and lengths.
5. **Terminations cluster in Madhya Pradesh** (282 of 1,200), then Odisha (123) and Assam (115).

## 5. The source
- `pmgsy.dord.gov.in`: ASP.NET MVC citizen reports in front of SSRS. No login, no captcha. Indian addresses only (the hub's proxies work).
- *Contractor Information* (per state × status): form, then report, then viewer, then CSV export (4 requests).
- *Agreement Details*: the state summary, then a **drill-through** (report viewer postback) on the Total row's "works awarded" cell
  (`249iT0:0`) and "awarded and terminated" cell (`293iT0:0`), then the CSV export.

### 5.1 Site map

| What | URL | Notes |
|---|---|---|
| Contractor master | `/MasterArea/Master/ContractorInformationLayout` → `ContractorInformationLayoutReport/` | per state × status (A, I, B, E) |
| Works awarded / terminated | `/WorkAwardedArea/WorkAwarded/TendAgrDetailsLayout` → `TendAgrDetailsReport/` → drill-through | per state; filters for year, batch, scheme |
| Also open, not scraped | KPI contractors' performance (`/dbweb`), quality-monitor grading, Final Bill Payment | aggregates |
| Officials' OMMAS | `pmgsygov.dord.gov.in` | login (officials) |

## 6. How it is collected
- **Code:** `adapters/pmgsy.py`. `token`, `iframe_src` and `export_url` follow the report chain; `parse_contractors` reads the
  contractor CSV; `drill_form` builds the drill-through postback (every hidden field sent back); `parse_works`,
  `mark_package_totals` and `work_id` handle the works.
- **Queue:** contractors `<state>-<status>` (148) plus monthly; works `agreements-<state>` (37) plus monthly. Each CSV is stored as it came.

## 7. The data
- Contractor record `<state>-<hash>`: `company`, `contact_person`, `registration_no`, `address`, `pincode`, `phone1/2`, `email`,
  `pan` (masked), `contractor_status`. **Phones and e-mails belong to people**: keep them out of published examples.
- Work record `<state>-awarded-<hash>` / `<state>-terminated-<hash>`: `district`, `block`, `sanction_year`, `sanction_date`, `batch`,
  `package`, `work_type` (`Road` 193,818 / `LSB` 12,135 / blank 34), `work_name`, `road_length_km`, `bridge_length_m`,
  `sanction_cost_lakh`, `awarded_cost_lakh`, and `awarded_is_package_total` (after PR #7).

```sql
-- awarded cost per state, counting a repeated package amount once
with w as (select data->>'state' st, data->>'package' pk, nullif(data->>'sanction_cost_lakh','')::numeric s,
                  nullif(data->>'awarded_cost_lakh','')::numeric a
           from public.records where project = 'contractor-registration-pmgsy-agreements' and data->>'kind' = 'pmgsy_work_awarded'),
p as (select st, pk, sum(s) s, case when count(distinct a) = 1 and count(*) > 1 then max(a) else sum(a) end a from w group by 1, 2)
select st, round(sum(s)/100) sanctioned_cr, round(sum(a)/100) awarded_cr from p group by 1 order by 3 desc;
-- blacklisted contractors
select data->>'state', data->>'company', data->>'registration_no' from public.records
where project = 'contractor-registration-pmgsy-contractors' and data->>'contractor_status' = 'Blacklisted';
```

## 8. Verification
- Tests: 42 passed (report chain, contractor CSV, drill-through form, works CSV, package totals). scrape-check through a proxy:
  Sikkim works, 1,263 records, same ids on rerun.
- Cross-checks: Sikkim's 1,215 awarded works equal the Agreement Details summary.
- **Not checked:** the summary totals for the other 36 states; why some states' awards run 2–3× above sanction.

## 9. Known gaps and quality issues

| # | Issue | Size | Impact / what to do |
|---|---|---:|---|
| 1 | **No contractor per work** (at the source, for the public) | all works | Try pmgsytenders.gov.in (GePNIC) for winners. |
| 2 | **Awarded cost repeated per package** (at the source) | 24,629 packages | Flag in PR #7; sum per package. |
| 3 | PAN masked (at the source) | 56,988 | First five and last character only. |
| 4 | Works without a work type (at the source) | 34 | Kept. |

## 10. Risks and open decisions
- **Risks:** a change to the report's drill-through cell ids makes the item fail ("FileName" check) rather than store another report.
- **To decide:** whether to add pmgsytenders.gov.in. It is a GePNIC portal, so it fits the `gepnic` family better (its owner would add it).

## 11. Next steps
**To do now:** 1. Merge PR #7.
**Later:** 2. KPI contractors' performance (`/dbweb`). 3. Winners per tender from pmgsytenders.gov.in (via the `gepnic` family).
4. Join PMGSY contractors to CPWD ([C01](report-C01.md)) and state registers ([C02](report-C02.md)) by firm name.
**Housekeeping:** none.

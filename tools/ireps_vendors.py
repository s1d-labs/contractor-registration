"""IREPS UVAM vendor directory (RDSO and other approving agencies' approved vendors): a manual, human-signed-in pull.

The directory is open to guests who sign in with an Indian mobile number, an image verification code and an OTP sent to that
phone. A person does the sign-in; this script only keeps the session and reads the directory pages in it, gently. Run it on a
team box: ireps.gov.in answers the box directly (2 Nov 2026), no proxy needed. Keep every step on the same address (the session is
tied to it): all on the box directly, or all through one `myproxy --hours 2 run …`.

    python tools/ireps_vendors.py login
        asks for the mobile number, shows the verification image (opens the PNG path it prints: VS Code shows it), asks for
        the code, sends the OTP, asks for the OTP. Saves the session and the first directory page.
    python tools/ireps_vendors.py fetch '<path or URL on ireps.gov.in>'      one more page in the same session
    python tools/ireps_vendors.py export                                      the whole directory (once mapped)

Nothing about the person is written anywhere: the mobile number and OTP are only sent to IREPS. The session cookies stay in
~/.cache/s1d/ireps-session.json (readable by you only) and expire on IREPS's side after a while. Pages go to ~/ireps-export/<date>/;
upload the result with `mybucket sync ~/ireps-export ireps-uvam` and delete the local copy afterwards.
Check the IREPS terms of use before each pull. One request every DELAY seconds; stop at the first refusal.
"""
import base64
import html
import json
import os
import re
import sys
import time
from datetime import date
from getpass import getpass
from pathlib import Path

import requests

SITE = "https://ireps.gov.in"
DIRECTORY = SITE + "/epsn/cvap/admintab/vndrDirectoryAnon.do?activity=displayFirst&approvAgencyCode=-2"
SESSION = Path.home() / ".cache" / "s1d" / "ireps-session.json"
OUT = Path.home() / "ireps-export" / date.today().isoformat()
DELAY = 2.0
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def session():
    s = requests.Session()
    s.headers["User-Agent"] = UA
    if SESSION.exists():
        s.cookies.update(json.loads(SESSION.read_text()))
    return s


def keep(s):
    SESSION.parent.mkdir(parents=True, exist_ok=True)
    SESSION.write_text(json.dumps(requests.utils.dict_from_cookiejar(s.cookies)))
    SESSION.chmod(0o600)


def save(name, text):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(text, encoding="utf-8")
    return path


def hidden(page, field):
    m = re.search(rf'name="{re.escape(field)}"[^>]*value="([^"]*)"', page)
    return html.unescape(m.group(1)) if m else ""


def login():
    s = session()
    s.cookies.clear()
    page = s.get(DIRECTORY, timeout=60).text
    form = re.search(r'<form name="guestLogonForm" method="post" action="([^"]+)"', page)
    if not form:
        sys.exit("The guest sign-in form was not found (IREPS changed the page, or the proxy is refused).")
    action = SITE + html.unescape(form.group(1))
    mobile = input("Mobile number (10 digits, +91; sent to IREPS only): ").strip()
    for _ in range(3):
        cap = s.post(SITE + "/epsn/generateCaptchaAction.do", timeout=60).json()
        img = save("verification.png", "")
        img.write_bytes(base64.b64decode(cap["imageCaptcha"]))
        code = input(f"Open {img} and type the verification code: ").strip()
        time.sleep(DELAY)
        r = s.post(action, timeout=60, data={"activity": "submitGetOTP", "mobileNo": mobile, "ccode": "91", "number": code,
                                             "ver": cap["newcaptcha"]})
        if "OK#" in r.text:
            break
        print(f"IREPS did not send the OTP: {re.sub(r'<[^>]+>|\s+', ' ', r.text)[:200]}")
    else:
        sys.exit("No OTP after three tries.")
    img.unlink(missing_ok=True)
    otp = getpass("OTP from the SMS (not shown): ").strip()
    time.sleep(DELAY)
    r = s.post(action, timeout=120, data={"org.apache.struts.taglib.html.TOKEN": hidden(page, "org.apache.struts.taglib.html.TOKEN"),
                                          "activity": "submitOTP", "actionMode": "vendorDirectory", "mobileNo": mobile, "ccode": "91",
                                          "ver": cap["newcaptcha"], "number": code, "otp": otp})
    if 'name="guestLogonForm"' in r.text:
        sys.exit("Still on the sign-in page: wrong or expired OTP.")
    keep(s)
    print(f"Signed in. Landing page: {save('landing.html', r.text)} ({r.url})")
    links = sorted(set(re.findall(r'(?:href|action)="(/epsn/[^"#]+)"', r.text)))
    print("Links and forms on it:", *links[:40], sep="\n  ")


def fetch(target):
    s = session()
    url = target if target.startswith("http") else SITE + target
    if not url.startswith(SITE + "/"):
        sys.exit("Only pages on ireps.gov.in.")
    time.sleep(DELAY)
    r = s.get(url, timeout=120)
    keep(s)
    if 'name="guestLogonForm"' in r.text:
        sys.exit("The session has expired: sign in again (login).")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("/epsn/", 1)[-1])[:120] + ".html"
    print(f"{r.status_code} {len(r.text)} chars -> {save(name, r.text)}")


def export():
    sys.exit("Not written yet: run `login` once and share the saved landing page, so the directory's pages can be mapped.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "login":
        login()
    elif cmd == "fetch" and len(sys.argv) > 2:
        fetch(sys.argv[2])
    elif cmd == "export":
        export()
    else:
        sys.exit(__doc__)

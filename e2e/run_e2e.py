"""Browser end-to-end test of the full stack (FastAPI + Vite build + real Chrome).

Usage: python e2e/run_e2e.py --api http://localhost:8000 --web http://localhost:4173 --image some_pest.jpg --out e2e/shots
Walks the main user journey and saves screenshots; exits non-zero on any failure.
"""
import argparse
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("--web", default="http://localhost:4173")
ap.add_argument("--image", required=True)
ap.add_argument("--out", default="e2e/shots")
ap.add_argument("--headed", action="store_true")
a = ap.parse_args()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
email = f"e2e{int(time.time())}@test.in"
errors: list[str] = []
steps: list[str] = []


def shot(page, name):
    page.screenshot(path=str(out / f"{name}.png"), full_page=True)


with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=not a.headed)
    ctx = b.new_context(viewport={"width": 1366, "height": 900}, accept_downloads=True)
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text}"))

    def step(name):
        steps.append(name); print("✓", name, flush=True)

    page.goto(a.web); expect(page.get_by_text("Save the harvest.")).to_be_visible(); shot(page, "01_landing"); step("landing")
    page.get_by_role("link", name="Get started").first.click()
    page.get_by_label("Full name").fill("E2E Kisan"); page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill("Secret123!"); page.get_by_role("button", name="Create account").click()
    expect(page.get_by_text("Profile & settings")).to_be_visible(); step("register → profile")
    page.get_by_role("button", name="Rice (Paddy) धान").click()
    page.locator("input[type=number]").nth(1).fill("21.1458"); page.locator("input[type=number]").nth(2).fill("79.0882")
    page.get_by_role("button", name="Save changes").click(); expect(page.get_by_text("Profile saved.")).to_be_visible()
    shot(page, "02_profile"); step("profile + farm + crops saved")

    page.goto(f"{a.web}/app/detect")
    page.locator("input[type=file]").set_input_files(a.image)
    page.get_by_label("Growth stage").select_option("flowering")
    page.get_by_role("button", name="Detect pests").click()
    expect(page.get_by_role("heading", name="Results")).to_be_visible(timeout=60000)
    shot(page, "03_detect_result"); step("upload + detect")
    page.get_by_role("link", name="Full analysis & treatment").first.click()
    expect(page.get_by_text("Infestation severity")).to_be_visible()
    page.get_by_text("How this score was calculated").click()
    shot(page, "04_report"); step("pest analysis report")
    with page.expect_download() as d:
        page.get_by_role("button", name="PDF report").click()
    pdf = d.value.path(); assert Path(pdf).read_bytes()[:4] == b"%PDF"; step("PDF download")

    page.goto(f"{a.web}/app/history"); expect(page.get_by_text("Detection history")).to_be_visible()
    expect(page.get_by_role("link", name="View report").first).to_be_visible()
    with page.expect_download() as d:
        page.get_by_role("button", name="Export CSV").click()
    assert Path(d.value.path()).read_text().startswith("id,date_utc"); shot(page, "05_history"); step("history + CSV")

    page.goto(f"{a.web}/app"); expect(page.get_by_text("Total scans")).to_be_visible(); shot(page, "06_dashboard"); step("dashboard")
    page.goto(f"{a.web}/app/analytics"); expect(page.get_by_text("Pest-wise distribution")).to_be_visible(); shot(page, "07_analytics"); step("analytics")
    page.goto(f"{a.web}/app/treatments/aphids"); expect(page.get_by_text("Organic options")).to_be_visible(); shot(page, "08_treatment"); step("treatments")

    page.goto(f"{a.web}/app/chat")
    page.get_by_role("button", name="Neem oil ka use kaise hota hai?").click()
    expect(page.get_by_text("Neem oil ka sahi upyog")).to_be_visible(timeout=60000)
    page.get_by_placeholder("Apna sawal likhiye").fill("Meri fasal mein kaun sa keeda laga hai?"); page.keyboard.press("Enter")
    page.wait_for_timeout(2500); shot(page, "09_chat"); step("chatbot (Hinglish)")

    page.goto(f"{a.web}/app/alerts"); expect(page.get_by_text("Notifications & alerts")).to_be_visible()
    page.get_by_role("button", name="Mark all read").click(); page.get_by_role("button", name="Alert thresholds").click()
    expect(page.get_by_text("Active thresholds")).to_be_visible(); shot(page, "10_alerts"); step("alerts + thresholds")
    page.goto(f"{a.web}/app/weather"); page.wait_for_timeout(3000); shot(page, "11_weather"); step("weather page renders")

    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{a.web}/app"); page.wait_for_timeout(1200); shot(page, "12_mobile_dashboard")
    page.get_by_role("button", name="Open menu").click(); page.wait_for_timeout(500); shot(page, "13_mobile_menu"); step("mobile layout + menu")
    page.goto(f"{a.web}/app/detect"); page.wait_for_timeout(800); shot(page, "14_mobile_detect")
    page.set_viewport_size({"width": 1366, "height": 900})
    page.goto(f"{a.web}/app"); page.get_by_role("button", name="Toggle dark mode").click(); page.wait_for_timeout(600)
    shot(page, "15_dark_dashboard"); step("dark mode")
    page.get_by_role("button", name="Log out").click(); expect(page).to_have_url(f"{a.web}/login"); step("logout")
    b.close()

errors = [e for e in errors if "favicon" not in e and "geolocation" not in e.lower()]
print(f"\n{len(steps)} steps passed")
if errors:
    print("Browser errors:\n" + "\n".join(errors[:20]))
    sys.exit(1)

#!/usr/bin/env python3
"""Standalone agent script to seed a cemetery, section, 3x3 grid, plots, and an interred person."""

import argparse
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone


def generate_slug(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower().strip("-"))
    return slug


def api_request(api_url, token, method, path, body=None, cemetery_id=None):
    url = f"{api_url.rstrip('/')}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if cemetery_id:
        headers["X-Cemetery-ID"] = cemetery_id

    data = json.dumps(body).encode("utf-8") if body is not None else None

    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            error_body = json.loads(raw)
        except json.JSONDecodeError:
            error_body = raw
        raise RuntimeError(
            f"Failed: {method} {path}\nStatus: {e.code}\nResponse: {json.dumps(error_body, indent=2)}"
        ) from e


class CemeterySeedAgent:
    def __init__(self, api_url, token=None, dry_run=False):
        self.api_url = api_url.rstrip("/")
        self.token = token
        self.dry_run = dry_run
        self.created = {
            "cemetery": None,
            "section": None,
            "grid": None,
            "plots": {},
            "interred": None,
        }

    def login(self, email, password):
        if self.dry_run:
            print(f"[DRY RUN] Would login with email: {email}")
            return
        result = api_request(self.api_url, None, "POST", "/v1/auth/login", {"email": email, "password": password})
        self.token = result["data"]["token"]

    def create_cemetery(self, payload):
        if self.dry_run:
            print(f"[DRY RUN] Would create cemetery:")
            print(json.dumps(payload, indent=2))
            self.created["cemetery"] = "<dry-run-cemetery-id>"
            return {"id": self.created["cemetery"]}
        result = api_request(self.api_url, self.token, "POST", "/v1/cemeteries", payload)
        self.created["cemetery"] = result["data"]["id"]
        return result["data"]

    def create_section(self, cemetery_id, payload):
        if self.dry_run:
            print(f"[DRY RUN] Would create section (cemetery: {cemetery_id}):")
            print(json.dumps(payload, indent=2))
            self.created["section"] = "<dry-run-section-id>"
            return {"id": self.created["section"]}
        result = api_request(self.api_url, self.token, "POST", "/v1/sections", payload, cemetery_id)
        self.created["section"] = result["data"]["id"]
        return result["data"]

    def create_grid(self, cemetery_id, section_id, payload):
        if self.dry_run:
            print(f"[DRY RUN] Would create grid (section: {section_id}):")
            print(json.dumps(payload, indent=2))
            self.created["grid"] = "<dry-run-grid-id>"
            return {"id": self.created["grid"]}
        result = api_request(self.api_url, self.token, "POST", f"/v1/sections/{section_id}/grids", payload, cemetery_id)
        self.created["grid"] = result["data"]["id"]
        return result["data"]

    def create_plot(self, cemetery_id, payload):
        plot_num = payload["plotNum"]
        if self.dry_run:
            print(f"[DRY RUN] Would create plot {plot_num}:")
            print(json.dumps(payload, indent=2))
            self.created["plots"][plot_num] = f"<dry-run-plot-{plot_num}-id>"
            return {"id": f"<dry-run-plot-{plot_num}-id>"}
        result = api_request(self.api_url, self.token, "POST", "/v1/plots", payload, cemetery_id)
        plot_num = payload["plotNum"]
        self.created["plots"][plot_num] = result["data"]["id"]
        return result["data"]

    def create_interred(self, cemetery_id, payload):
        if self.dry_run:
            print(f"[DRY RUN] Would create interred person:")
            print(json.dumps(payload, indent=2))
            self.created["interred"] = "<dry-run-interred-id>"
            return {"id": self.created["interred"]}
        result = api_request(self.api_url, self.token, "POST", "/v1/interred", payload, cemetery_id)
        self.created["interred"] = result["data"]["id"]
        return result["data"]

    def _generate_plot_geometry(self, row, col, base_lng=-122.0, base_lat=37.0, cell_w=0.00002, cell_h=0.00002, gap=0.000005):
        lng = base_lng + (col - 1) * (cell_w + gap)
        lat = base_lat - (row - 1) * (cell_h + gap)
        return {
            "type": "Polygon",
            "coordinates": [[
                [lng, lat],
                [lng, lat - cell_h],
                [lng + cell_w, lat - cell_h],
                [lng + cell_w, lat],
                [lng, lat],
            ]],
        }

    def _print_created(self):
        c = self.created
        print("\nCreated so far:")
        print(f"  cemetery: {c['cemetery']}")
        print(f"  section: {c['section']}")
        print(f"  grid: {c['grid']}")
        if c["plots"]:
            print(f"  plots: {', '.join(c['plots'].keys())}")
        if c["interred"]:
            print(f"  interred: {c['interred']}")

    def run(self, config):
        try:
            if not self.dry_run:
                if not self.token and config.get("email") and config.get("password"):
                    self.login(config["email"], config["password"])

                if not self.token:
                    print("Error: No token available. Provide --token or --email/--password.", file=sys.stderr)
                    sys.exit(1)

            cemetery_payload = {
                "name": config["cemetery_name"],
                "slug": config.get("cemetery_slug") or generate_slug(config["cemetery_name"]),
                "description": "Cemetery created by Python seed agent",
                "location": "Demo Location",
                "address": "123 Memory Lane",
                "city": "Demo City",
                "state": "CA",
                "zipCode": "00000",
            }
            cemetery = self.create_cemetery(cemetery_payload)
            cemetery_id = cemetery["id"]
            print(f"Created cemetery: {cemetery_id}")

            section_payload = {
                "name": config["section_name"],
                "slug": config.get("section_slug") or generate_slug(config["section_name"]),
                "description": "Section created by Python seed agent",
            }
            if config.get("section_address"):
                section_payload["streetAddress"] = config["section_address"]
            if config.get("section_city"):
                section_payload["city"] = config["section_city"]
            if config.get("section_state"):
                section_payload["state"] = config["section_state"]
            if config.get("section_zip"):
                section_payload["zipCode"] = config["section_zip"]
            section = self.create_section(cemetery_id, section_payload)
            section_id = section["id"]
            print(f"Created section: {section_id}")

            grid_payload = {
                "name": config.get("grid_name", "Demo 3x3 Grid"),
                "rows": 3,
                "columns": 3,
                "plotWidth": 9.8,
                "plotHeight": 6.6,
                "gap": 1.6,
                "startingPlot": str(config.get("starting_plot_num", 9001)),
                "plotDirection": "row",
            }
            grid = self.create_grid(cemetery_id, section_id, grid_payload)
            grid_id = grid["id"]
            print(f"Created grid: {grid_id}")

            starting_plot_num = config.get("starting_plot_num", 9001)
            plot_labels = []
            for row in range(1, 4):
                for col in range(1, 4):
                    plot_num = starting_plot_num + (row - 1) * 3 + (col - 1)
                    plot_labels.append((row, col, str(plot_num)))

            for row, col, label in plot_labels:
                geometry = self._generate_plot_geometry(row, col)
                plot_payload = {
                    "sectionId": section_id,
                    "gridId": grid_id,
                    "plotNum": label,
                    "slug": label.lower(),
                    "status": config.get("plot_status", "interred"),
                    "geometry": geometry,
                    "gridRow": row,
                    "gridColumn": col,
                    "rowSpan": 1,
                    "colSpan": 1,
                }
                plot = self.create_plot(cemetery_id, plot_payload)
                print(f"Created plot: {label} -> {plot['id']} (status: {plot.get('status', 'unknown')})")

            interred_plot_id = self.created["plots"]["9002"]
            dob = config.get("date_of_birth") or "1940-01-01T00:00:00.000Z"
            dod = config.get("date_of_death") or "2020-01-01T00:00:00.000Z"
            interred_payload = {
                "firstName": config["interred_first_name"],
                "lastName": config["interred_last_name"],
                "dateOfBirth": dob,
                "dateOfDeath": dod,
                "biography": "Biography created by Python seed agent",
                "isVeteran": config.get("is_veteran", True),
                "paymentStatus": config.get("payment_status", "paid"),
                "sectionId": section_id,
                "plotId": interred_plot_id,
            }
            interred = self.create_interred(cemetery_id, interred_payload)
            print(f"Created interred: {config['interred_first_name']} {config['interred_last_name']} -> {interred['id']} (plotId: {interred_plot_id})")

            print("\nSeeding complete.")
            self._print_created()

        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            self._print_created()
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Seed cemetery data via the API")
    parser.add_argument("--api-url", default=os.environ.get("CEMETERY_API_URL", "http://localhost:3001"))
    parser.add_argument("--token", default=os.environ.get("CEMETERY_API_TOKEN"))
    parser.add_argument("--email", default=os.environ.get("CEMETERY_API_EMAIL"))
    parser.add_argument("--password", default=os.environ.get("CEMETERY_API_PASSWORD"))
    parser.add_argument("--cemetery-name", default="Sample Cemetery")
    parser.add_argument("--cemetery-slug")
    parser.add_argument("--section-name", default="Section A")
    parser.add_argument("--section-slug")
    parser.add_argument("--section-address")
    parser.add_argument("--section-city")
    parser.add_argument("--section-state")
    parser.add_argument("--section-zip")
    parser.add_argument("--starting-plot-num", type=int, default=9001)
    parser.add_argument("--grid-name", default="Demo 3x3 Grid")
    parser.add_argument("--interred-first-name", default="John")
    parser.add_argument("--interred-last-name", default="Doe")
    parser.add_argument("--date-of-birth")
    parser.add_argument("--date-of-death")
    parser.add_argument("--is-veteran", action="store_true")
    parser.add_argument("--plot-status", default="interred")
    parser.add_argument("--payment-status", default="paid")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = {
        "cemetery_name": args.cemetery_name,
        "cemetery_slug": args.cemetery_slug,
        "section_name": args.section_name,
        "section_slug": args.section_slug,
        "section_address": args.section_address,
        "section_city": args.section_city,
        "section_state": args.section_state,
        "section_zip": args.section_zip,
        "starting_plot_num": args.starting_plot_num,
        "grid_name": args.grid_name,
        "interred_first_name": args.interred_first_name,
        "interred_last_name": args.interred_last_name,
        "date_of_birth": args.date_of_birth,
        "date_of_death": args.date_of_death,
        "is_veteran": args.is_veteran,
        "plot_status": args.plot_status,
        "payment_status": args.payment_status,
        "email": args.email,
        "password": args.password,
    }

    agent = CemeterySeedAgent(api_url=args.api_url, token=args.token, dry_run=args.dry_run)
    agent.run(config)


if __name__ == "__main__":
    main()

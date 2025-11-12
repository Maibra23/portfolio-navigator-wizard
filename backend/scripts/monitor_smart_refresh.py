#!/usr/bin/env python3
import json
import time
import urllib.error
import urllib.request

URL = "http://localhost:8000/api/portfolio/ticker-table/smart-refresh/preview"


def fetch_status():
    with urllib.request.urlopen(URL, timeout=5) as resp:
        return json.load(resp)


def main():
    print("Monitoring smart-refresh status (Ctrl+C to exit)", flush=True)
    while True:
        try:
            data = fetch_status()
            missing = data.get("missing_counts", {})
            samples = data.get("missing_samples", {})
            line = (
                f"{time.strftime('%H:%M:%S')} | "
                f"expired={data.get('expired_count', 0)} "
                f"prices={missing.get('prices', 0)} "
                f"sector={missing.get('sector', 0)} "
                f"metrics={missing.get('metrics', 0)}"
            )
            print(line)

            details = []
            if samples.get("metrics"):
                details.append("metrics: " + ", ".join(samples["metrics"][:5]))
            if samples.get("prices"):
                details.append("prices: " + ", ".join(samples["prices"][:3]))
            if samples.get("sector"):
                details.append("sector: " + ", ".join(samples["sector"][:3]))
            if details:
                print("    samples -> " + " | ".join(details))
        except KeyboardInterrupt:
            print("\nStopping monitor.")
            break
        except Exception as err:
            print(f"{time.strftime('%H:%M:%S')} | error: {err}")

        time.sleep(5)


if __name__ == "__main__":
    main()


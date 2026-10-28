from urllib.request import urlopen


if __name__ == "__main__":
    with urlopen("http://localhost:8000/health", timeout=5) as response:
        raise SystemExit(0 if response.status == 200 else 1)

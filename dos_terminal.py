import argparse
import socket
import sys
import time
from datetime import datetime

import requests

TIMEOUT_SECONDS = 5


def current_time() -> str:
    return datetime.now().strftime("%H:%M:%S")


def resolve_host_port(target: str, protocol: str, port_arg: int | None) -> tuple[str, int]:
    if ":" in target and protocol in {"TCP", "UDP"}:
        host, port_text = target.rsplit(":", 1)
        if port_text.isdigit():
            return host, int(port_text)
    if port_arg is not None:
        return target, int(port_arg)
    return target, 443 if protocol == "HTTPS" else 80


def check_http(target: str) -> str:
    if not target.startswith(("http://", "https://")):
        target = f"http://{target}"
    response = requests.get(target, timeout=TIMEOUT_SECONDS)
    return f"HTTP {response.status_code}"


def check_https(target: str) -> str:
    if not target.startswith("https://"):
        target = f"https://{target.lstrip('http://').lstrip('https://')}"
    response = requests.get(target, timeout=TIMEOUT_SECONDS)
    return f"HTTPS {response.status_code}"


def check_tcp(target: str, port_arg: int | None) -> str:
    host, port = resolve_host_port(target, "TCP", port_arg)
    with socket.create_connection((host, port), timeout=TIMEOUT_SECONDS):
        pass
    return f"TCP OK {host}:{port}"


def check_udp(target: str, port_arg: int | None) -> str:
    host, port = resolve_host_port(target, "UDP", port_arg)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(TIMEOUT_SECONDS)
        sock.sendto(b"ping", (host, port))
    return f"UDP wysłano do {host}:{port}"


def perform_check(target: str, protocol: str, port_arg: int | None = None) -> str:
    if protocol == "HTTP":
        return check_http(target)
    if protocol == "HTTPS":
        return check_https(target)
    if protocol == "TCP":
        return check_tcp(target, port_arg)
    if protocol == "UDP":
        return check_udp(target, port_arg)
    raise ValueError("Nieznany protokół")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Terminalowa wersja narzędzia do testowania połączeń")
    parser.add_argument("target", help="Adres routera lub URL")
    parser.add_argument("--protocol", choices=["HTTP", "HTTPS", "TCP", "UDP"], default="HTTP")
    parser.add_argument("--port", type=int, help="Port dla TCP/UDP")
    parser.add_argument("--rate", type=int, default=1, help="Ilość testów na sekundę (0 = bez przerwy)")
    parser.add_argument("--count", type=int, default=0, help="Liczba testów do wykonania (0 = nieskończenie)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.protocol in {"TCP", "UDP"} and args.port is None:
        print("Podaj port za pomocą --port dla TCP/UDP.", file=sys.stderr)
        sys.exit(2)

    if args.rate < 0:
        print("Szybkość musi być większa lub równa 0.", file=sys.stderr)
        sys.exit(2)

    if args.count < 0:
        print("Liczba testów musi być większa lub równa 0.", file=sys.stderr)
        sys.exit(2)

    print(f"Rozpoczęto test dla: {args.target} ({args.protocol})")

    iterations = 0
    try:
        while True:
            try:
                status_text = perform_check(args.target, args.protocol, args.port)
                print(f"[{current_time()}] {args.protocol} -> {status_text}")
            except Exception as exc:
                print(f"[{current_time()}] {args.protocol} -> Błąd: {exc}")

            iterations += 1
            if args.count and iterations >= args.count:
                break

            if args.rate == 0:
                continue
            time.sleep(max(0.001, 1 / args.rate))
    except KeyboardInterrupt:
        print("\nZatrzymano test.")


if __name__ == "__main__":
    main()

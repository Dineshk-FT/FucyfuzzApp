#!/usr/bin/env python3
"""
Improved length-attack module for Fucyfuzz / FucyFuzz - VCAN0 VERSION.

ADAPTED FOR VCAN0 (Classic CAN simulation on virtual interface)

Features:
- Arbitrary DLC field width support (e.g. 3-bit, 4-bit, 5-bit...).
- Classic CAN DLC handling (0-8 bytes only for vcan0 simulation).
- Forced DLC vs payload mismatches (malformed frames).
- Multiple payload patterns (random, 0x00, 0xFF, 0xAA/0x55, incremental).
- Burst sending, interval control, repeat loop.
- Basic listening thread to capture responses / error frames (best-effort).
- Uses python-can socketcan with vcan0 interface.
- Explicit [SUCCESS] / [FAIL] logging for every signal.

Note: vcan0 typically simulates Classic CAN, so CAN-FD features are disabled.
"""

import argparse
import os
import sys
import time
import random
import threading
import datetime
import errno

try:
    import can
except Exception:
    can = None

# Classic CAN DLC -> payload length mapping (0-8 bytes only)
CLASSIC_DLC_MAP = {
    0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8
}


def dlc_to_length(dlc: int, use_fd: bool) -> int:
    """Return actual payload length for a given DLC value (Classic CAN only for vcan0)."""
    # Force Classic CAN mapping for vcan0
    return CLASSIC_DLC_MAP.get(dlc, 8 if dlc > 8 else dlc)


def make_payload(pattern: str, length: int, start_byte: int = 0) -> bytes:
    """
    Build payload of requested length using pattern:
      - 'rand' => os.urandom
      - 'zeros' => 0x00 * length
      - 'ffs' => 0xFF * length
      - 'aa' => 0xAA * length
      - '55' => 0x55 * length
      - 'inc' => incremental bytes from start_byte
      - 'custom:<hexstring>' => repeats/truncates provided hex bytes
    """
    if length <= 0:
        return b""

    pattern = (pattern or "rand").lower()

    if pattern == "rand":
        return os.urandom(length)
    if pattern == "zeros":
        return bytes([0x00] * length)
    if pattern == "ffs":
        return bytes([0xFF] * length)
    if pattern == "aa":
        return bytes([0xAA] * length)
    if pattern == "55":
        return bytes([0x55] * length)
    if pattern == "inc":
        return bytes(((start_byte + i) & 0xFF) for i in range(length))
    if pattern.startswith("custom:"):
        hexs = pattern.split(":", 1)[1].strip()
        # accept 'aabbcc' or 'aa bb cc'
        hexs = hexs.replace(" ", "")
        try:
            raw = bytes.fromhex(hexs)
            if not raw:
                return os.urandom(length)
            # repeat or cut to length
            return (raw * ((length // len(raw)) + 1))[:length]
        except Exception:
            return os.urandom(length)

    # unknown pattern fallback
    return os.urandom(length)


def send_message(bus, arb_id: int, payload: bytes, dlc: int = None, is_fd: bool = False, extended: bool = False):
    """
    Construct and send a python-can Message for vcan0 (Classic CAN).
    Note: vcan0 typically ignores is_fd and dlc overrides beyond 8.
    """
    if can is None:
        raise RuntimeError("python-can is not installed/available in this environment.")

    # Build message kwargs - FORCE Classic CAN for vcan0
    kwargs = {
        "arbitration_id": arb_id, 
        "is_extended_id": extended,
        "data": payload,
        "is_fd": False  # Force Classic CAN for vcan0
    }

    # Only set DLC if provided and within Classic CAN range
    if dlc is not None and 0 <= dlc <= 8:
        kwargs["dlc"] = dlc

    msg = can.Message(**kwargs)
    
    try:
        bus.send(msg)
        return True
    except Exception as e:
        # We suppress the print here to handle logging in the main loop, 
        # or we can print it if needed.
        return False


def listen_for_responses(bus, stop_event, log_func=None):
    """
    Simple background receiver loop that logs frames seen on the vcan0 bus.
    """
    if can is None:
        return

    try:
        while not stop_event.is_set():
            try:
                msg = bus.recv(timeout=0.2)
            except Exception as e:
                # Timeout or other recv issues - continue
                msg = None

            if msg is None:
                continue

            text = "[RECV] ID=0x{0:X} DLC={1} LEN={2} FD={3} DATA={4}".format(
                getattr(msg, "arbitration_id", 0),
                getattr(msg, "dlc", len(getattr(msg, "data", b""))),
                len(getattr(msg, "data", b"")),
                getattr(msg, "is_fd", False),
                getattr(msg, "data", b"").hex()
            )
            if log_func:
                log_func(text)
            else:
                print(text)
    except Exception as e:
        # exit quietly
        try:
            if log_func:
                log_func(f"[Listener] stopped due to: {e}")
        except Exception:
            pass


def run_lenattack_on_bus(bus,
                         targets,
                         min_dlc,
                         max_dlc,
                         dlc_bits,
                         fd,
                         mismatch_prob,
                         pattern,
                         interval,
                         bursts,
                         repeat,
                         start_byte,
                         quiet,
                         logfile=None):
    """
    Core attack loop for vcan0 - Classic CAN focused.
    """
    # For vcan0, limit DLC to Classic CAN range (0-8)
    max_dlc = min(max_dlc, 8)
    min_dlc = max(min_dlc, 0)
    
    # Force Classic CAN mode regardless of fd parameter
    fd = False

    stop_event = threading.Event()
    listener = threading.Thread(target=listen_for_responses, args=(bus, stop_event, None), daemon=True)
    listener.start()

    log_fp = None
    if logfile:
        try:
            log_fp = open(logfile, "a", buffering=1)
            log_fp.write("# lenattack vcan0 log started: %s\n" % datetime.datetime.now().isoformat())
        except Exception as e:
            print(f"[WARN] Could not open logfile {logfile}: {e}")
            log_fp = None

    try:
        while True:
            for arb in targets:
                for dlc in range(min_dlc, max_dlc + 1):
                    canonical_len = dlc_to_length(dlc, use_fd=fd)

                    # decide whether to send a mismatched payload
                    if random.random() < mismatch_prob:
                        # For vcan0, limit mismatch testing to 0-8 bytes
                        cand_len = random.randint(0, 8)
                        if cand_len == canonical_len:
                            cand_len = (cand_len + 1) % 9
                        payload_len = cand_len
                    else:
                        payload_len = canonical_len

                    # generate payload using requested pattern
                    payload = make_payload(pattern, payload_len, start_byte=start_byte)

                    # attempt sending 'bursts' times to stress target
                    for b in range(bursts):
                        ts = datetime.datetime.now().isoformat()
                        status_str = "FAIL"
                        details = ""
                        
                        try:
                            success = send_message(bus, arb, payload, dlc=dlc, is_fd=fd, extended=False)
                            
                            if success:
                                status_str = "SUCCESS"
                                details = f"SEND ID=0x{arb:X} DLC={dlc} LEN={len(payload)} DATA={payload.hex()}"
                            else:
                                status_str = "FAIL"
                                details = f"SEND ID=0x{arb:X} DLC={dlc} LEN={len(payload)} (Socket/Bus Error)"
                            
                            # Construct the final log line
                            out_line = f"{ts} [{status_str}] {details}"
                            
                            if not quiet:
                                print(out_line)
                            if log_fp:
                                log_fp.write(out_line + "\n")
                                
                        except Exception as e:
                            # Handle unexpected exceptions not caught by send_message
                            err_line = f"{ts} [FAIL] ERROR sending to 0x{arb:X}: {e}"
                            print(err_line)
                            if log_fp:
                                log_fp.write(err_line + "\n")
                                
                        # small delay between burst frames
                        time.sleep(max(0.0, interval))

                    # small delay between DLC steps
                    time.sleep(max(0.0, interval))

            if not repeat:
                break
    except KeyboardInterrupt:
        print("\nInterrupted by user - stopping length attack.")
    finally:
        # stop listener
        stop_event.set()
        listener.join(timeout=1.0)
        if log_fp:
            log_fp.write("# lenattack log ended: %s\n" % datetime.datetime.now().isoformat())
            log_fp.close()


def parse_targets(raw_targets):
    """
    Accept strings like 'any' or '0x123' or '291' or a range '0x100-0x1FF' or comma-separated.
    Returns list of integer arbitration IDs.
    """
    out = []
    for token in raw_targets:
        token = token.strip()
        if not token:
            continue
        if token.lower() == "any":
            # full standard 11-bit CAN: 0x000..0x7FF
            out.extend(range(0x000, 0x800))
            continue
        if "-" in token:
            a, b = token.split("-", 1)
            try:
                start = int(a, 0)
                end = int(b, 0)
                out.extend(range(start, end + 1))
            except Exception:
                pass
            continue
        # single ID
        try:
            out.append(int(token, 0))
        except Exception:
            print(f"[WARN] Could not parse target token: {token}")
    # dedupe while preserving order
    seen = set()
    deduped = []
    for v in out:
        if v not in seen:
            deduped.append(v)
            seen.add(v)
    return deduped


def open_vcan0_bus():
    """Open a python-can socketcan bus on vcan0 interface."""
    if can is None:
        raise RuntimeError("python-can not installed")
    
    try:
        bus = can.interface.Bus(channel='vcan0', bustype='socketcan')
        print("[INFO] Successfully opened vcan0 interface")
        return bus
    except Exception as e:
        print(f"[ERROR] Could not open vcan0: {e}")
        print("[INFO] You may need to create vcan0 interface first:")
        print("       sudo modprobe vcan")
        print("       sudo ip link add dev vcan0 type vcan")
        print("       sudo ip link set up vcan0")
        raise


def module_main(argv_list=None):
    parser = argparse.ArgumentParser(prog="fucyfuzz lenattack-vcan0",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description="Improved length attack sender for VCAN0 (Classic CAN simulation).",
                                     epilog="VCAN0 Examples:\n"
                                            "  fucyfuzz lenattack-vcan0 0x123\n"
                                            "  fucyfuzz lenattack-vcan0 --min-dlc 0 --max-dlc 8 --pattern rand 0x123\n"
                                            "  fucyfuzz lenattack-vcan0 --targets 0x100-0x1FF --repeat --log out.txt\n"
                                            "\nNote: vcan0 simulates Classic CAN (DLC 0-8 only, no CAN-FD)\n"
                                     )
    parser.add_argument("targets", nargs="+", help="Target arbitration IDs (hex/dec), 'any', ranges like 0x100-0x1FF")
    parser.add_argument("--min-dlc", type=int, default=0, help="Minimum DLC value to try (default 0)")
    parser.add_argument("--max-dlc", type=int, default=8, help="Maximum DLC value to try (default 8 for Classic CAN)")
    parser.add_argument("--dlc-bits", type=int, default=4, help="Width (bits) of DLC field to simulate (default 4)")
    parser.add_argument("--fd", action="store_true", default=False, help="[IGNORED for vcan0] CAN-FD not supported on vcan0")
    parser.add_argument("--mismatch-prob", type=float, default=0.5, help="Probability to send mismatched payload lengths (0..1)")
    parser.add_argument("--pattern", type=str, default="inc",
                        help="Payload pattern: rand|zeros|ffs|aa|55|inc|custom:deadbeef")
    parser.add_argument("--interval", type=float, default=0.05, help="Interval between sends (s)")
    parser.add_argument("--bursts", type=int, default=1, help="Frames to send per DLC step")
    parser.add_argument("--repeat", action="store_true", help="Repeat sweep until interrupted")
    parser.add_argument("--start-byte", type=int, default=0, help="Start byte for 'inc' pattern")
    parser.add_argument("--quiet", action="store_true", help="Minimize console output")
    parser.add_argument("--log", type=str, default=None, help="Append output to logfile")
    args = parser.parse_args(argv_list)

    # Warn about ignored FD parameter
    if args.fd:
        print("[INFO] CAN-FD ignored for vcan0 (using Classic CAN simulation only)")

    targets = parse_targets(args.targets)
    if not targets:
        print("No valid targets. Exiting.")
        return

    # Open vcan0 interface
    try:
        bus = open_vcan0_bus()
    except Exception as e:
        print(f"ERROR: Could not open vcan0 interface: {e}")
        return

    try:
        run_lenattack_on_bus(bus=bus,
                             targets=targets,
                             min_dlc=max(0, args.min_dlc),
                             max_dlc=max(0, min(args.max_dlc, 8)),  # Force max 8 for vcan0
                             dlc_bits=max(1, args.dlc_bits),
                             fd=False,  # Force Classic CAN for vcan0
                             mismatch_prob=min(max(0.0, args.mismatch_prob), 1.0),
                             pattern=args.pattern,
                             interval=max(0.0, args.interval),
                             bursts=max(1, args.bursts),
                             repeat=args.repeat,
                             start_byte=max(0, args.start_byte) & 0xFF,
                             quiet=args.quiet,
                             logfile=args.log)
    finally:
        # Cleanup
        try:
            if hasattr(bus, "shutdown"):
                bus.shutdown()
            if hasattr(bus, "close"):
                bus.close()
        except Exception:
            pass


if __name__ == "__main__":
    module_main(sys.argv[1:])
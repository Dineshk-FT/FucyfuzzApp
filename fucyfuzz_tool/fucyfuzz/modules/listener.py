from fucyfuzz.utils.can_actions import CanActions
from sys import stdout
from collections import Counter
import argparse
import time

def start_listener(falling_sort):
    found_arb_ids = Counter()
    print("Running listener (press Ctrl+C to exit)")

    try:
        with CanActions(notifier_enabled=False) as can_wrap:
            bus = can_wrap.bus

            while True:
                # BLOCKING RECEIVE with timeout
                msg = bus.recv(0.2)
                if msg is None:
                    continue

                arb_id = msg.arbitration_id

                # First time seeing this ID → print
                if arb_id not in found_arb_ids:
                    print(
                        "\rLast ID: 0x{0:08x} ({1} unique arbitration IDs found)".format(
                            arb_id, len(found_arb_ids) + 1
                        ),
                        end=" "
                    )
                    stdout.flush()

                found_arb_ids[arb_id] += 1

    except KeyboardInterrupt:
        print("\n\nDetected arbitration IDs:")
        if len(found_arb_ids) == 0:
            print("No arbitration IDs were detected.")
            return

        sorted_ids = sorted(
            found_arb_ids.items(),
            key=lambda x: x[1],
            reverse=falling_sort
        )
        for arb_id, hits in sorted_ids:
            print("Arb id 0x{0:08x} {1} hits".format(arb_id, hits))


def parse_args(args):
    parser = argparse.ArgumentParser(
        prog="fucyfuzz listener",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Passive listener module for Fucyfuzz"
    )
    parser.add_argument(
        "-r", "--reverse",
        action="store_true",
        help="Reversed sorting of results",
    )
    return parser.parse_args(args)


def module_main(args):
    args = parse_args(args)
    start_listener(args.reverse)

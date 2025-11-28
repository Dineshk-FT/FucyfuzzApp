# DCM
> _**Note**: This module has been replaced by the [UDS](uds.md) module. It is still supported by Fucyfuzz due to legacy reasons._

```
$ fucyfuzz dcm -h

-------------------
FUCYFUZZ v0.x
-------------------

Loaded module 'dcm'

usage: fucyfuzz dcm [-h] {discovery,services,subfunc,dtc} ...

Diagnostics module for Fucyfuzz

positional arguments:
  {discovery,services,subfunc,dtc}

optional arguments:
  -h, --help            show this help message and exit

Example usage:
  fucyfuzz dcm discovery
  fucyfuzz dcm services 0x733 0x633
  fucyfuzz dcm subfunc 0x733 0x633 0x22 2 3
  fucyfuzz dcm dtc 0x7df 0x7e8
 ```

## Discovery
```
$ fucyfuzz dcm discovery -h

-------------------
FUCYFUZZ v0.x
-------------------

Loaded module 'dcm'

usage: fucyfuzz dcm discovery [-h] [-min MIN] [-max MAX] [-nostop]
                           [-blacklist B [B ...]] [-autoblacklist N]

optional arguments:
  -h, --help            show this help message and exit
  -min MIN
  -max MAX
  -nostop               scan until end of range
  -blacklist B [B ...]  arbitration IDs to ignore
  -autoblacklist N      scan for interfering signals for N seconds and
                        blacklist matching arbitration IDs
```

## Services
````
$ fucyfuzz dcm services -h

-------------------
FUCYFUZZ v0.x
-------------------

Loaded module 'dcm'

usage: fucyfuzz dcm services [-h] src dst

positional arguments:
  src         arbitration ID to transmit from
  dst         arbitration ID to listen to

optional arguments:
  -h, --help  show this help message and exit
````

## Subfunc
````
$ fucyfuzz dcm subfunc -h

-------------------
FUCYFUZZ v0.x
-------------------

Loaded module 'dcm'

usage: fucyfuzz dcm subfunc [-h] [-show] src dst service i [i ...]

positional arguments:
  src         arbitration ID to transmit from
  dst         arbitration ID to listen to
  service     service ID (e.g. 0x22 for Read DID)
  i           sub-function indices

optional arguments:
  -h, --help  show this help message and exit
  -show       show data in terminal
````

## DTC
````
$ fucyfuzz dcm dtc -h

-------------------
FUCYFUZZ v0.x
-------------------

Loaded module 'dcm'

usage: fucyfuzz dcm dtc [-h] [-clear] src dst

positional arguments:
  src         arbitration ID to transmit from
  dst         arbitration ID to listen to

optional arguments:
  -h, --help  show this help message and exit
  -clear      Clear DTC / MIL
````

# XCP
```
-------------------
FUCYFUZZ v0.x
-------------------

Loaded module 'xcp'

usage: fucyfuzz xcp [-h] {discovery,info,dump} ...

XCP module for Fucyfuzz

positional arguments:
 {discovery,info,dump}

optional arguments:
 -h, --help            show this help message and exit

Example usage:
 fucyfuzz xcp discovery
 fucyfuzz xcp info 1000 1001
 fucyfuzz xcp dump 0x3e8 0x3e9 0x1fffb000 0x4800 -f bootloader.hex
 ```
 
## Discovery
 ```
-------------------
FUCYFUZZ v0.x
-------------------

Loaded module 'xcp'

usage: fucyfuzz xcp discovery [-h] [-min MIN] [-max MAX]

optional arguments:
 -h, --help            show this help message and exit
 -min MIN
 -max MAX
 ```
 
## Info
 
 ```
-------------------
FUCYFUZZ v0.x
-------------------

Loaded module 'xcp'

usage: fucyfuzz xcp info [-h] src dst

positional arguments:
  src         arbitration ID to transmit from
  dst         arbitration ID to listen to

optional arguments:
 -h, --help            show this help message and exit
 ```
 
## Dump
 
 ```
-------------------
FUCYFUZZ v0.x
-------------------

Loaded module 'xcp'

usage: fucyfuzz xcp dump [-h] [-f F] src dst start length

positional arguments:
  src         arbitration ID to transmit from
  dst         arbitration ID to listen to
  start       start adress
  length      dump length

optional arguments:
 -h, --help            show this help message and exit
 -f F, -file F         output file
 ```

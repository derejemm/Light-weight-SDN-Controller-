# Technology Switching Module

## Overview
This Python module(In OBU devices) provides unified control for switching between ITS-G5 and CV2X communication technologies in vehicular networks. It handles service management, process monitoring, and fallback mechanisms for reliable technology transitions.

## Key Features
- **Dual-mode switching**: ITS-G5 (DSRC) ↔ CV2X (C-V2X)
- **Complete lifecycle management**: Start/stop/check operations
- **Automatic verification**: Connection health checks
- **Robust cleanup**: Force termination of stuck processes
- **Logging**: Detailed operation logs in `/mnt/rw/log/`

# Technology Switching Module - Complete Parameter Specification

## ITS-G5 Parameters
| Parameter       | CLI Argument | Default   | Valid Range       | Description                          |
|-----------------|--------------|-----------|-------------------|--------------------------------------|
| Channel        | `-c`         | 184       | 172-184           | DSRC channel number                  |
| Antenna        | `-a`         | 3         | 1-4               | Antenna selection index              |
| Packet Length  | `-l`         | 50        | 10-1500           | Payload length (bytes)               |
| MCS Index      | `-m`         | R12QPSK   | R1QPSK-R27QAM64   | Modulation and Coding Scheme         |
| Packet Rate    | `-r`         | 100       | 10-1000           | Packets per second                   |
| TX Power       | `-p`         | 30        | 10-33             | Transmission power (dBm)             |
| Window Type    | `-w`         | CCH       | CCH/SCH           | Channel type selection               |

Example TX Command:
llc -i0 test-tx -c 178 -a 2 -l 300 -m R9QPSK -r 200 -p 23

## CV2X (PC5 Interface) Parameters
| Parameter       | CLI Argument | Default   | Valid Range       | Description                          |
|-----------------|--------------|-----------|-------------------|--------------------------------------|
| Packet Length  | `-l`         | 300       | 64-1500            | UDP payload size (bytes)             |
| TX Power       | in `-W`      | 23        | 10-33              | Peak transmission power (dBm)        |
| MCS Index      | in `-W`      | 5         | 0-15               | 3GPP MCS index                       |
| Retransmission | in `-W`      | 0         | 0=Disable<br>1=Enable<br>2=Don't care | HARQ retransmission policy |
| TX Pool ID     | in `-W`      | (none)    | (none)             | Optional resource pool identifier    |

ACME Tool Syntax:
acme -l 300 -W 23,7,1,2 -k 1000 -m tx_log.txt > tx_output.txt

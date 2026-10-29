# ICMP Ping (Python)

A custom `ping` utility written in Python with raw sockets. It builds ICMP Echo Request packets by hand (including the checksum), sends one per second, measures round-trip time, translates ICMP error replies into readable messages, and prints a summary when you stop it.

**Course:** NSCOM02 (De La Salle University) | **Machine Project:** MCO1

---

## Features

- **Hand-built ICMP packets:** the Echo Request (type 8) header, timestamp payload, and Internet checksum are constructed with `struct` rather than a ping library.
- **Per-packet output:** each reply shows the source address, the sequence field from the reply, the TTL read from the IP header, and the round-trip time in milliseconds.
- **Reply matching:** replies are matched to the request using the process ID in the ICMP identifier field, so unrelated ICMP traffic is ignored.
- **ICMP error parsing:** when an Echo Reply does not arrive, the ICMP type and code are decoded into a plain-language message, for example:
  - **Type 3 (Destination Unreachable), codes 0-15:** network/host/protocol/port unreachable, fragmentation needed, administratively prohibited, and others
  - **Type 5 (Redirect), codes 0-3**
  - **Type 11 (Time Exceeded), codes 0-1:** TTL exceeded in transit or reassembly
  - **Type 12 (Parameter Problem), codes 0-2**
- **Session summary:** on `Ctrl+C`, prints packets sent and received, the packet-loss percentage, and the minimum, average, and maximum RTT.

### Defaults

| Setting | Value |
|---|---|
| Reply timeout | 2 seconds |
| Interval between probes | 1 second |

## How it works

1. A raw ICMP socket is opened and an Echo Request is sent to the resolved IP address.
2. The program waits (via `select`) for a response up to the timeout.
3. The reply's IP header is skipped (20 bytes) and the ICMP header is unpacked to read the type, code, identifier, and sequence fields.
4. An Echo Reply (type 0) with a matching identifier yields the RTT, computed from the timestamp stored in the packet payload. ICMP error types are mapped to messages. No response in time prints `Request timed out.`
5. Any probe that does not produce an Echo Reply (a timeout or an ICMP error) is counted as lost in the summary.

## Requirements

- Python 3 (standard library only, no extra packages)
- **Administrator / root privileges.** Raw sockets require elevated rights.

## Usage

Run from an elevated terminal.

**Windows** (open Command Prompt or PowerShell as Administrator):

```
py ICMP.py google.com
```

**Linux / macOS:**

```
sudo python3 ICMP.py google.com
```

If you omit the host, the program asks for one:

```
Enter target host:
```

Press `Ctrl+C` to stop and see the summary.

## Output format

```
Pinging <ip-address> using Python (Ctrl+C to end):

Reply from <ip-address>: seq=<n> ttl=<n> time=<ms>ms
Request timed out.
[Err] <ICMP error description> (Type <t>, Code <c>)

Packets sent: <n>, packets received: <n>, <x.xx>% packet loss
RTT min: <ms>ms, RTT avg: <ms>ms, RTT max: <ms>ms
```

## Testing error handling

Real ICMP errors are hard to trigger on demand, so `ICMP.py` contains commented-out test hooks for simulating them:

- In `receiveOnePing`, uncomment the `type`/`code` override to force a Destination Unreachable response and check the message mapping.
- In `doOnePing`, uncomment the `IP_TTL` socket option to send packets with a very small TTL and provoke a Time Exceeded reply from a router.

Re-comment these lines for normal use.

## Limitations

- IPv4 only.
- One probe at a time; it runs until interrupted.
- The sequence field in the Echo Request header is fixed at 1, so the `seq` shown in replies does not count up.
- An unresolvable hostname raises an exception instead of a friendly message.
- ICMP may be blocked by firewalls or by the target, which appears as timeouts.

## Related

The same packet-building and checksum logic is reused in the traceroute project (NSCOM02 MCO2).

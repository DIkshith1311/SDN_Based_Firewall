# SDN-Based Firewall using Mininet and POX

**Author:** Dikshith Varma M N
**USN:** PES1UG24AM363

---

## Table of Contents

1. [Introduction](#introduction)
2. [Objective](#objective)
3. [Technologies Used](#technologies-used)
4. [Network Topology](#network-topology)
5. [System Architecture](#system-architecture)
6. [Firewall Implementation](#firewall-implementation)
7. [How to Run](#how-to-run)
8. [Testing and Results](#testing-and-results)
9. [SDN Concepts Applied](#sdn-concepts-applied)
10. [Conclusion](#conclusion)
11. [References](#references)

---

## Introduction

Software Defined Networking (SDN) is a modern networking paradigm that fundamentally changes how networks are designed and managed. It achieves this by separating the **control plane** — the logic that decides how traffic should be routed — from the **data plane** — the hardware that actually forwards the packets.

In a traditional network, every switch and router contains its own built-in logic for making forwarding decisions. This tight coupling makes it difficult to update policies, respond to threats, or reconfigure the network without touching each device individually. SDN eliminates this constraint by moving all decision-making into a single centralized software entity called the **controller**. Switches become simple forwarding devices that follow instructions sent to them by the controller over a standardized protocol — **OpenFlow**.

This project exploits that architecture to build a **software-defined firewall**. Instead of deploying a dedicated hardware firewall device, all filtering logic lives in the controller. When a packet arrives at the switch, the switch asks the controller what to do with it. The controller evaluates the packet against a set of rules and either instructs the switch to forward it or to drop it — and installs a flow rule so the switch can handle future matching packets on its own, without consulting the controller again.

---

## Objective

- Demonstrate the practical separation of control plane and data plane in an SDN environment
- Implement a packet filtering firewall entirely in software using the POX controller
- Use the OpenFlow protocol to install flow rules (forwarding and drop) dynamically on a virtual switch
- Emulate a realistic network using Mininet and validate firewall behavior through ping tests, bandwidth tests, and flow table inspection

---

## Technologies Used

| Tool / Technology | Role in the Project |
|---|---|
| **Mininet** | Emulates the network topology — creates virtual hosts, switches, and links on a single Linux machine |
| **POX Controller** | Python-based SDN controller that runs the firewall logic and communicates with the switch over OpenFlow |
| **Python 3.8** | Language used to write the firewall module (`firewall.py`) inside POX |
| **OpenFlow 1.0** | Protocol used for communication between the POX controller and the Open vSwitch |
| **Open vSwitch (OVS)** | Software switch embedded in Mininet that supports OpenFlow and executes the flow rules |
| **iperf** | Network benchmarking tool used to measure TCP throughput and verify whether connections are truly blocked or allowed |
| **ovs-ofctl** | Command-line utility to inspect the flow table inside the switch and verify installed rules |

---

## Network Topology

The project uses a **single switch topology** — the simplest SDN topology — where all hosts connect to one central switch, which is managed by a remote controller.

```
        h1  (10.0.0.1)
         |
         |
        s1  ─────────────── POX Controller
       /    \                (Remote, port 6633)
     h2      h3
(10.0.0.2)  (10.0.0.3)
```

| Component | Description |
|---|---|
| `h1` | Host 1 — IP address `10.0.0.1` — source of blocked traffic |
| `h2` | Host 2 — IP address `10.0.0.2` — target of the firewall rule |
| `h3` | Host 3 — IP address `10.0.0.3` — unaffected host, used to verify allowed traffic |
| `s1` | Open vSwitch — forwards or drops packets based on flow rules sent by the controller |
| POX Controller | Runs `firewall.py` — intercepts new flows, applies rules, installs flow entries |

This topology is intentionally minimal. The focus is not on complex routing but on demonstrating how a controller can selectively permit or deny communication between specific hosts using flow-level rules.

---

## System Architecture

### How Traffic Flows Through the System

When Mininet starts, switch `s1` connects to the POX controller over TCP on port `6633`. From this point on, the controller has full visibility and control over every new flow passing through the switch.

The process for each new packet is as follows:

1. **Packet arrives at the switch** — A host sends a packet (e.g., h1 tries to ping h2). Since no flow rule exists yet for this packet, the switch cannot handle it on its own.

2. **packet_in event** — The switch encapsulates the packet and sends it to the controller as a `packet_in` message via OpenFlow.

3. **Controller inspects the packet** — The POX firewall module extracts the source IP and destination IP from the packet header.

4. **Rule matching** — The controller checks the source-destination pair against the configured blocked list.

5. **Decision and flow installation:**
   - If the packet **matches a blocked rule**, the controller sends a `flow_mod` message to the switch instructing it to install a **drop rule** with high priority (`priority=200`). All subsequent packets matching this rule will be silently dropped at the switch, without being sent to the controller again.
   - If the packet **does not match any blocked rule**, the controller identifies the correct output port and installs a **forwarding rule** (`priority=10`). The packet is also forwarded immediately (via `packet_out`).

6. **Controller logs the event** — For every blocked flow, the firewall module logs the source and destination IP to the terminal.

This reactive model means the controller is only consulted for the *first* packet of each new flow. Once a flow rule is installed in the switch, all subsequent matching packets are handled directly by the switch — making the system efficient despite the initial controller lookup overhead.

---

## Firewall Implementation

### Firewall Rule

One rule is enforced in this project, demonstrating the core concept clearly:

| Source | Destination | Action |
|---|---|---|
| `10.0.0.1` (h1) | `10.0.0.2` (h2) | **DROP** |
| Any other source | Any other destination | **FORWARD** |

### Controller Module — `firewall.py`

The firewall is implemented as a POX component. The module listens for `packet_in` events and processes each incoming packet as follows:

- Parse the Ethernet frame and extract the IPv4 layer
- Read the source IP (`nw_src`) and destination IP (`nw_dst`)
- Check whether the (src, dst) pair appears in the blocked rules list
- If **blocked**:
  - Construct an OpenFlow `flow_mod` with `actions=[]` (empty action list = drop)
  - Set `priority=200` to ensure this rule overrides any general forwarding rules
  - Match on `dl_type=0x0800` (IPv4), `nw_src`, and `nw_dst`
  - Send the `flow_mod` to the switch
  - Log: `BLOCKED: <src> → <dst>`
- If **allowed**:
  - Use the switch's MAC address table to determine the output port
  - Install a forwarding flow rule and forward the current packet

The learning switch behavior (MAC learning for normal traffic) is integrated alongside the firewall logic, so the switch handles all other traffic intelligently without flooding every packet.

### Why High Priority Matters

OpenFlow switches match packets against flow rules in priority order — highest priority first. By assigning `priority=200` to drop rules and `priority=10` to forwarding rules, the firewall guarantees that a blocked flow can never accidentally match a lower-priority forwarding rule. The drop rule always wins.

---

## How to Run

### Prerequisites

- Ubuntu 20.04 or later
- Mininet: `sudo apt install mininet`
- POX controller: `git clone https://github.com/noxrepo/pox`
- Python 3.8

### Step 1 — Place the Firewall Module

Copy `firewall.py` into the POX forwarding components directory:

```bash
cp firewall.py ~/pox/pox/forwarding/
```

### Step 2 — Start the POX Controller

In the first terminal, navigate to the POX directory and start the controller with INFO-level logging:

```bash
cd ~/pox
python3.8 pox.py log.level --INFO firewall
```

You should see output indicating the firewall module has loaded and POX is waiting for a switch to connect.

### Step 3 — Launch the Mininet Topology

In a second terminal, start Mininet with a single-switch topology of three hosts, pointing to the remote controller:

```bash
sudo mn --topo single,3 --controller remote
```

Once Mininet starts, switch `s1` will connect to the POX controller automatically. The controller terminal will log the connection.

### Step 4 — Run Tests

From the Mininet CLI, run the tests described in the section below.

---

## Testing and Results

### 7.1 Ping Test — Blocked Traffic

```bash
mininet> h1 ping h2
```

**What happens:** h1 sends ICMP echo requests to h2. The first packet triggers a `packet_in` event at the controller. The controller identifies the source (`10.0.0.1`) and destination (`10.0.0.2`) as a blocked pair, installs a drop rule in the switch, and logs the event. All packets — including the first — are dropped.

**Result:** 4 packets transmitted, 0 received — **100% packet loss**.

---

### 7.2 Ping Test — Allowed Traffic

```bash
mininet> h2 ping h3
```

**What happens:** h2 sends ICMP echo requests to h3. This pair is not in the blocked list, so the controller installs a forwarding rule. Packets flow normally between h2 and h3.

**Result:** 7 packets transmitted, 7 received — **0% packet loss**, with round-trip times in the sub-millisecond range after the first controller lookup.

---

### 7.3 Full Connectivity Test — pingall

```bash
mininet> pingall
```

**What happens:** Mininet tests all possible host pairs: h1↔h2, h1↔h3, h2↔h3.

**Result:** 33% packet drop (4 out of 6 packets received). The two dropped paths are `h1 → h2` and `h2 → h1`, confirming bidirectional blocking. All other pairs communicate successfully.

---

### 7.4 Bandwidth Test — iperf (Allowed)

```bash
mininet> h2 iperf -s &
mininet> h3 iperf -c h2
```

**What happens:** h3 opens a TCP connection to h2 on port 5001. Since this is an allowed flow, the controller installs a forwarding rule and traffic flows unobstructed.

**Result:** TCP connection established successfully. Measured bandwidth — **47.6 Gbits/sec** (expected for virtual links in Mininet). Confirms that allowed flows experience full, unimpeded throughput.

---

### 7.5 Bandwidth Test — iperf (Blocked)

```bash
mininet> h2 iperf -s &
mininet> h1 iperf -c h2
```

**What happens:** h1 attempts to open a TCP connection to h2. The SYN packet triggers a `packet_in` event. The controller identifies it as a blocked flow, installs a drop rule, and the TCP handshake never completes. iperf on h1 hangs indefinitely waiting for a response that will never arrive.

**Result:** TCP connection attempt initiated — no data transferred, no bandwidth reported. The connection stalls, confirming the firewall blocks at the packet level before any session is established.

---

### 7.6 Flow Table Inspection

```bash
sudo ovs-ofctl dump-flows s1
```

**What happens:** This command queries the Open vSwitch directly and prints all currently installed flow entries.

**Key entries observed:**

| Priority | Match | Action |
|---|---|---|
| `200` | `ip, nw_src=10.0.0.1, nw_dst=10.0.0.2` | `drop` |
| `10` | `dl_src=<h3-mac>, dl_dst=<h2-mac>` | `output:"s1-eth2"` |
| `10` | `dl_src=<h2-mac>, dl_dst=<h3-mac>` | `output:"s1-eth3"` |

The `priority=200` drop rule confirms the controller has correctly programmed the switch. The `n_packets` counter on this rule increments with each blocked packet, verifying it is actively being matched in real time.

---

### 7.7 Controller Log Output

When the firewall detects a blocked flow, the POX terminal prints:

```
INFO:firewall: Final Firewall + Learning Switch Loaded
INFO:core:POX 0.7.0 (gar) is up.
INFO:openflow.of_01:[00-00-00-00-00-01 2] connected
INFO:firewall:Switch [00-00-00-00-00-01 2] connected
INFO:firewall: BLOCKED: 10.0.0.1 → 10.0.0.2
```

This log appears the first time h1 attempts to communicate with h2. Subsequent packets from the same flow are dropped directly by the switch and never reach the controller — so the log entry appears only once per flow, demonstrating the efficiency of reactive flow installation.

---

### Results Summary

| Test | Direction | Expected | Observed |
|---|---|---|---|
| Ping | h1 → h2 | Blocked | 100% packet loss ✅ |
| Ping | h2 → h3 | Allowed | 0% packet loss ✅ |
| pingall | All pairs | h1↔h2 blocked | 33% dropped (4/6) ✅ |
| iperf | h3 → h2 | Allowed, high BW | 47.6 Gbits/sec ✅ |
| iperf | h1 → h2 | Blocked, no data | Connection stalled ✅ |
| Flow table | s1 | Drop rule present | priority=200 drop confirmed ✅ |
| Controller log | POX terminal | BLOCKED logged | Logged once per flow ✅ |

All tests produced the expected results, confirming correct firewall behavior across every test scenario.

---

## SDN Concepts Applied

| Concept | How It Is Used in This Project |
|---|---|
| **Control Plane Separation** | All forwarding and filtering decisions are made exclusively by the POX controller, not the switch |
| **Data Plane Execution** | Open vSwitch executes only the flow rules it has been given — it performs no independent decision-making |
| **OpenFlow Protocol** | `packet_in` events carry new packets to the controller; `flow_mod` messages carry rules back to the switch |
| **Reactive Flow Installation** | Flow rules are installed on-demand when the first packet of a new flow arrives — not pre-programmed |
| **Match–Action Model** | Each flow rule specifies a match condition (src IP, dst IP) and an action (drop or output port) |
| **Flow Priority** | Drop rules use `priority=200`; forwarding rules use `priority=10` — firewall rules always take precedence |
| **Centralized Policy Enforcement** | A single controller enforces consistent traffic policy across the entire network from one place |

---

## Conclusion

This project demonstrates that a fully functional network firewall can be implemented purely in software using SDN principles — without any dedicated hardware, without manually configuring each switch, and with the ability to update rules dynamically at runtime.

The POX controller intercepts new flows, evaluates them against firewall rules, and programs the Open vSwitch accordingly. Blocked traffic (h1 → h2) is dropped with zero packet delivery. Allowed traffic (h2 ↔ h3) flows at full virtual link speed. The flow table, controller logs, ping results, and iperf benchmarks all confirm that the system behaves correctly and consistently.

The broader implication is that SDN enables network security policies to be treated as software — version-controlled, programmatically updated, and centrally managed. This makes SDN-based firewalls significantly more flexible and maintainable than traditional hardware-based approaches, especially in dynamic environments such as data centers and cloud networks.

### Potential Future Extensions

- Add port-based filtering (block specific TCP/UDP ports, e.g., HTTP on port 80)
- Implement time-based rules that activate or deactivate based on a schedule
- Migrate to a production-grade controller framework such as **Ryu** or **ONOS**
- Build a real-time monitoring dashboard that visualizes active flow rules and blocked events
- Extend to multi-switch topologies to test firewall policy consistency across a larger network

---

## References

- [Mininet Official Documentation](http://mininet.org/walkthrough/)
- [POX Controller Wiki](https://noxrepo.github.io/pox-doc/html/)
- [OpenFlow 1.0 Specification](https://opennetworking.org/wp-content/uploads/2013/04/openflow-spec-v1.0.0.pdf)
- [Open vSwitch Documentation](https://docs.openvswitch.org/)
- Feamster, N., Rexford, J., & Zegura, E. (2014). *The Road to SDN: An Intellectual History of Programmable Networks*. ACM SIGCOMM Computer Communication Review.

---

> **Course:** Computer Networks / SDN Lab
> **Institution:** PES University

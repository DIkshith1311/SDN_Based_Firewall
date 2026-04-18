# SDN-Based Firewall using Mininet and POX

**Author:** Dikshith Varma M N
**USN:** PES1UG24AM363

---

## Table of Contents

1. [Introduction](#introduction)
2. [Objective](#objective)
3. [Technologies Used](#technologies-used)
4. [Network Topology](#network-topology)
5. [Firewall Rule](#firewall-rule)
6. [How to Run](#how-to-run)
7. [Testing and Results](#testing-and-results)
8. [Flow Table Verification](#flow-table-verification)
9. [Controller Logs](#controller-logs)
10. [SDN Concepts Applied](#sdn-concepts-applied)
11. [Conclusion](#conclusion)

---

## Introduction

Software Defined Networking (SDN) is a network architecture that decouples the **control plane** (decision-making logic) from the **data plane** (packet forwarding). This separation allows network behavior to be programmatically controlled through a centralized software controller.

In traditional networks, routing and filtering logic is embedded within each hardware device, making policy changes complex and error-prone. SDN addresses this limitation by delegating all control decisions to a centralized controller, which communicates with network switches using the **OpenFlow protocol**.

This project implements a **software-defined firewall** that leverages SDN principles to enforce traffic filtering rules dynamically, without requiring dedicated firewall hardware.

---

## Objective

- Understand and demonstrate the SDN architecture (control plane vs. data plane separation)
- Implement firewall logic using the POX SDN controller and OpenFlow protocol
- Simulate a network environment using Mininet
- Validate traffic control through ping tests, iperf performance tests, and flow table inspection

---

## Technologies Used

| Tool / Technology | Purpose |
|---|---|
| **Mininet** | Network emulator for creating virtual topologies |
| **POX Controller** | Python-based SDN controller for implementing firewall logic |
| **Python 3.8** | Programming language for controller module development |
| **OpenFlow Protocol** | Communication protocol between the controller and switches |
| **Open vSwitch (OVS)** | Software switch used within Mininet |
| **iperf** | Network performance testing tool (bandwidth measurement) |

---

## Network Topology

This project uses a **single switch topology** consisting of three hosts connected to one central switch, managed by a remote POX controller.

```
        h1  (10.0.0.1)
         |
         |
        s1  ──── Remote Controller (POX)
       /    \
     h2      h3
(10.0.0.2)  (10.0.0.3)
```

**Components:**

- `s1` — Open vSwitch (software switch)
- `h1` — Host 1, IP: `10.0.0.1`
- `h2` — Host 2, IP: `10.0.0.2`
- `h3` — Host 3, IP: `10.0.0.3`
- POX Controller — Runs externally, connected to `s1` via OpenFlow

---

## Firewall Rule

The following traffic filtering rule is enforced by the controller:

| Direction | Action |
|---|---|
| `h1 (10.0.0.1)` → `h2 (10.0.0.2)` | **BLOCK (DROP)** |
| All other traffic | **ALLOW (FORWARD)** |

**How it works:**

When a packet arrives at switch `s1`, it triggers a `packet_in` event at the controller. The controller inspects the source and destination IP addresses. If the packet matches the blocked rule, the controller installs a **high-priority drop rule** in the switch's flow table. Otherwise, the packet is forwarded normally, and a forwarding rule is installed for subsequent packets.

---

## How to Run

### Prerequisites

- Ubuntu (or compatible Linux distribution)
- Mininet installed (`sudo apt install mininet`)
- POX controller cloned (`git clone https://github.com/noxrepo/pox`)
- Python 3.8

### Step 1 — Clone the Repository

```bash
git clone <your-repo-link>
cd <repo-folder>
```

### Step 2 — Copy Firewall Module to POX

Place the `firewall.py` file inside the POX components directory:

```bash
cp firewall.py ~/pox/pox/forwarding/
```

### Step 3 — Start the POX Controller

Open a terminal and run:

```bash
python3.8 pox.py log.level --INFO firewall
```

The controller will start and listen for switch connections.

### Step 4 — Start the Mininet Topology

Open a second terminal and run:

```bash
sudo mn --topo single,3 --controller remote
```

Mininet will launch the topology and connect switch `s1` to the POX controller.

---

## Testing and Results

### 7.1 Ping Test

#### Blocked Traffic — `h1 → h2`

```bash
mininet> h1 ping h2
```

**Result:** 100% packet loss — firewall rule successfully drops all packets from h1 to h2.

![Blocked Ping](screenshots/Blocked_Ping.jpeg)

---

#### Allowed Traffic — `h2 → h3`

```bash
mininet> h2 ping h3
```

**Result:** 7 packets transmitted, 7 received, 0% packet loss — communication is successful.

![Allowed Ping](screenshots/Allowed_ping.jpeg)

---

### 7.2 Performance Test using iperf

#### Allowed Flow — `h3 → h2`

```bash
mininet> h2 iperf -s &
mininet> h3 iperf -c h2
```

**Result:** TCP connection established successfully. Bandwidth measured at **47.6 Gbits/sec**, confirming unobstructed high-throughput communication.

![iperf Allowed](screenshots/iperf_allowed.jpeg)

---

#### Blocked Flow — `h1 → h2`

```bash
mininet> h2 iperf -s &
mininet> h1 iperf -c h2
```

**Result:** TCP connection attempt initiated but no data transferred — the firewall rule prevents the connection from completing.

![iperf Blocked](screenshots/iperf_blocked.jpeg)

---

### 7.3 Network Connectivity Test (pingall)

```bash
mininet> pingall
```

**Result:** 33% packet drop (4/6 received). The `h1 → h2` and `h2 → h1` paths are blocked by the firewall; all other host pairs communicate successfully.

![pingall Output](screenshots/pingall.jpeg)

---

### Summary of Results

| Test | Direction | Result |
|---|---|---|
| Ping | `h1 → h2` | Blocked (100% packet loss) |
| Ping | `h2 → h3` | Successful (0% packet loss) |
| pingall | All hosts | 33% dropped — h1 ↔ h2 blocked, rest reachable |
| iperf | `h3 → h2` | 47.6 Gbits/sec — high bandwidth, successful |
| iperf | `h1 → h2` | Connection stalled — blocked |

---

## Flow Table Verification

After running the tests, the flow rules installed in switch `s1` were verified using:

```bash
sudo ovs-ofctl dump-flows s1
```

The output confirms the presence of:

- A **drop rule** with `priority=200` matching `nw_src=10.0.0.1, nw_dst=10.0.0.2` with `actions=drop`
- **Forwarding rules** for all other active flows with `actions=output`

![Flow Table](screenshots/dump_.jpeg)

---

## Controller Logs

The POX controller was started with INFO-level logging, which prints a message each time a blocked flow is detected:

```bash
python3.8 pox.py log.level --INFO firewall
```

**Sample log output:**

```
INFO:firewall: Final Firewall + Learning Switch Loaded
INFO:core:POX 0.7.0 (gar) is up.
INFO:openflow.of_01:[00-00-00-00-00-01 2] connected
INFO:firewall:Switch [00-00-00-00-00-01 2] connected
INFO:firewall: BLOCKED: 10.0.0.1 → 10.0.0.2
```

The log confirms the firewall module loaded correctly, the switch connected to the controller, and blocked traffic was detected and logged in real time.

![Controller Logs](screenshots/firewall_controller_log.jpeg)

---

## SDN Concepts Applied

| Concept | Implementation in this Project |
|---|---|
| **Control Plane** | POX Controller — makes all forwarding and drop decisions |
| **Data Plane** | Open vSwitch (`s1`) — forwards packets based on installed flow rules |
| **OpenFlow Protocol** | Used for controller-switch communication (`packet_in`, `flow_mod`) |
| **Flow Rules (Match–Action)** | Match on src/dst IP → Action: drop or forward |
| **Centralized Network Control** | Single controller manages all traffic decisions for the entire topology |
| **Reactive Flow Installation** | Flow rules are installed only when the first packet of a flow arrives |

---

## Conclusion

This project demonstrates the practical implementation of a network firewall using Software Defined Networking principles. By centralizing control logic in the POX controller and leveraging the OpenFlow protocol for switch communication, the system achieves dynamic, policy-driven traffic management without dedicated hardware.

The implemented firewall successfully blocks unauthorized communication (h1 → h2) while allowing all other traffic to flow normally. Results from ping tests, iperf benchmarks, flow table inspection, and controller logs confirm that the firewall rules are correctly enforced at the switch level. This experiment validates SDN as an effective and flexible approach to network security and traffic control.

---

> **Course:** Computer Networks / SDN Lab
> **Institution:** PES University

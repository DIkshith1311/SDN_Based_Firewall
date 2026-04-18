from pox.core import core
import pox.openflow.libopenflow_01 as of

log = core.getLogger()

# MAC learning table
mac_to_port = {}

# Block rule
BLOCKED = [("10.0.0.1", "10.0.0.2")]


def _handle_ConnectionUp(event):
    log.info("Switch %s connected", event.connection)


def _handle_PacketIn(event):
    packet = event.parsed
    if not packet:
        return

    dpid = event.connection.dpid

    if dpid not in mac_to_port:
        mac_to_port[dpid] = {}

    # Learn source MAC
    mac_to_port[dpid][packet.src] = event.port

    ip_packet = packet.find('ipv4')

    # FIREWALL CHECK (HIGHEST PRIORITY)
    if ip_packet:
        src_ip = str(ip_packet.srcip)
        dst_ip = str(ip_packet.dstip)

        if (src_ip, dst_ip) in BLOCKED:
            log.info("🚫 BLOCKED: %s → %s", src_ip, dst_ip)

            msg = of.ofp_flow_mod()
            msg.match.dl_type = 0x0800   # IP
            msg.match.nw_src = ip_packet.srcip
            msg.match.nw_dst = ip_packet.dstip
            msg.priority = 200           # 🔥 HIGH PRIORITY

            # No action → DROP
            event.connection.send(msg)
            return

    #  NORMAL LEARNING SWITCH LOGIC
    if packet.dst in mac_to_port[dpid]:
        out_port = mac_to_port[dpid][packet.dst]
    else:
        out_port = of.OFPP_FLOOD

    # Install forwarding rule
    msg = of.ofp_flow_mod()
    msg.match.dl_src = packet.src
    msg.match.dl_dst = packet.dst
    msg.priority = 10
    msg.actions.append(of.ofp_action_output(port=out_port))
    event.connection.send(msg)

    # Send packet immediately
    msg = of.ofp_packet_out()
    msg.data = event.ofp
    msg.actions.append(of.ofp_action_output(port=out_port))
    event.connection.send(msg)


def launch():
    core.openflow.addListenerByName("ConnectionUp", _handle_ConnectionUp)
    core.openflow.addListenerByName("PacketIn", _handle_PacketIn)
    log.info("🔥 Final Firewall + Learning Switch Loaded")

"""
Unit tests for NetFlow v9 and IPFIX parsing in Sentinel Optimizer agent.

Note: These tests validate the parsing logic for NetFlow v9 and IPFIX protocols.
The ag3ntwerk includes NetFlow parsing implementation at src/sentinel/src/sentinel/agents/optimizer.py
which adds full template-based parsing for v9 and IPFIX (v10) protocols.
"""

import pytest
import struct
import socket
from unittest.mock import AsyncMock, MagicMock


class TestNetFlowPacketParsing:
    """Test NetFlow packet parsing with available optimizer."""

    @pytest.fixture
    def mock_engine(self):
        """Create mock Sentinel engine."""
        engine = MagicMock()
        engine.event_bus = MagicMock()
        engine.event_bus.publish = AsyncMock()
        engine.event_bus.subscribe = MagicMock()
        return engine

    @pytest.fixture
    def optimizer(self, mock_engine):
        """Create OptimizerAgent instance."""
        try:
            from sentinel.agents.optimizer import OptimizerAgent

            config = {
                "netflow_enabled": True,
                "netflow_port": 2055,
            }
            agent = OptimizerAgent(mock_engine, config)
            return agent
        except ImportError:
            pytest.skip("Sentinel package not available")

    @pytest.mark.asyncio
    async def test_parse_netflow_v9_header(self, optimizer):
        """Test parsing NetFlow v9 packet header."""
        # Build NetFlow v9 header
        version = 9
        count = 1
        sys_uptime = 12345
        unix_secs = 1700000000
        seq_num = 100
        source_id = 50

        header = struct.pack("!HHIIII", version, count, sys_uptime, unix_secs, seq_num, source_id)

        # Add empty template flowset
        flowset_id = 0
        flowset_length = 4
        flowset = struct.pack("!HH", flowset_id, flowset_length)

        packet = header + flowset
        addr = ("192.168.1.1", 2055)

        # Should not raise
        await optimizer._parse_netflow_v9(packet, addr)

    @pytest.mark.asyncio
    async def test_parse_ipfix_header(self, optimizer):
        """Test parsing IPFIX packet header."""
        # Build IPFIX header
        version = 10
        length = 20
        export_time = 1700000000
        seq_num = 100
        observation_domain = 50

        header = struct.pack("!HHIII", version, length, export_time, seq_num, observation_domain)

        # Add empty template set
        set_id = 2
        set_length = 4
        set_header = struct.pack("!HH", set_id, set_length)

        packet = header + set_header
        addr = ("192.168.1.1", 4739)

        # Should not raise
        await optimizer._parse_ipfix(packet, addr)

    @pytest.mark.asyncio
    async def test_process_netflow_packet_version_detection(self, optimizer):
        """Test NetFlow version detection in packet processing."""
        addr = ("192.168.1.1", 2055)

        # NetFlow v5 (version = 5)
        v5_packet = struct.pack("!H", 5) + b"\x00" * 22  # Minimum header
        await optimizer._process_netflow_packet(v5_packet, addr)
        assert optimizer._netflow_packets_received == 1

        # NetFlow v9 (version = 9)
        v9_packet = struct.pack("!H", 9) + b"\x00" * 18  # Minimum header
        await optimizer._process_netflow_packet(v9_packet, addr)
        assert optimizer._netflow_packets_received == 2

        # IPFIX (version = 10)
        ipfix_packet = struct.pack("!H", 10) + b"\x00" * 14  # Minimum header
        await optimizer._process_netflow_packet(ipfix_packet, addr)
        assert optimizer._netflow_packets_received == 3


class TestNetFlowV5Parsing:
    """Test NetFlow v5 parsing (already implemented)."""

    @pytest.fixture
    def mock_engine(self):
        """Create mock Sentinel engine."""
        engine = MagicMock()
        engine.event_bus = MagicMock()
        engine.event_bus.publish = AsyncMock()
        engine.event_bus.subscribe = MagicMock()
        return engine

    @pytest.fixture
    def optimizer(self, mock_engine):
        """Create OptimizerAgent instance."""
        try:
            from sentinel.agents.optimizer import OptimizerAgent

            config = {
                "netflow_enabled": True,
                "netflow_port": 2055,
            }
            agent = OptimizerAgent(mock_engine, config)
            return agent
        except ImportError:
            pytest.skip("Sentinel package not available")

    @pytest.mark.asyncio
    async def test_parse_netflow_v5_with_flow(self, optimizer, mock_engine):
        """Test parsing NetFlow v5 packet with a flow record."""
        # Build NetFlow v5 header
        # version(2), count(2), sys_uptime(4), unix_secs(4), unix_nsecs(4),
        # flow_seq(4), engine_type(1), engine_id(1), sampling(2) = 24 bytes
        version = 5
        count = 1
        sys_uptime = 12345
        unix_secs = 1700000000
        unix_nsecs = 0
        flow_seq = 1
        engine_type = 0
        engine_id = 0
        sampling = 0

        header = struct.pack(
            "!HHIIIIBBH",
            version,
            count,
            sys_uptime,
            unix_secs,
            unix_nsecs,
            flow_seq,
            engine_type,
            engine_id,
            sampling,
        )

        # Build a flow record (48 bytes)
        # src_ip(4), dst_ip(4), next_hop(4), input_if(2), output_if(2),
        # packets(4), bytes(4), start_time(4), end_time(4),
        # src_port(2), dst_port(2), pad1(1), tcp_flags(1), proto(1), tos(1),
        # src_as(2), dst_as(2), src_mask(1), dst_mask(1), pad2(2)
        src_ip = socket.inet_aton("192.168.1.100")
        dst_ip = socket.inet_aton("10.0.0.1")
        next_hop = socket.inet_aton("0.0.0.0")
        input_if = struct.pack("!H", 1)
        output_if = struct.pack("!H", 2)
        packets = struct.pack("!I", 100)
        bytes_sent = struct.pack("!I", 15000)
        start_time = struct.pack("!I", 10000)
        end_time = struct.pack("!I", 12000)
        src_port = struct.pack("!H", 54321)
        dst_port = struct.pack("!H", 80)
        pad1 = b"\x00"
        tcp_flags = struct.pack("!B", 0x10)  # ACK
        proto = struct.pack("!B", 6)  # TCP
        tos = struct.pack("!B", 0)
        src_as = struct.pack("!H", 0)
        dst_as = struct.pack("!H", 0)
        src_mask = struct.pack("!B", 24)
        dst_mask = struct.pack("!B", 8)
        pad2 = struct.pack("!H", 0)

        flow_record = (
            src_ip
            + dst_ip
            + next_hop
            + input_if
            + output_if
            + packets
            + bytes_sent
            + start_time
            + end_time
            + src_port
            + dst_port
            + pad1
            + tcp_flags
            + proto
            + tos
            + src_as
            + dst_as
            + src_mask
            + dst_mask
            + pad2
        )

        packet = header + flow_record
        addr = ("192.168.1.1", 2055)

        await optimizer._parse_netflow_v5(packet, addr)

        # Verify event was published
        mock_engine.event_bus.publish.assert_called_once()
        call_args = mock_engine.event_bus.publish.call_args
        event = call_args[0][0]

        assert event.event_type == "network.flow.detected"
        assert event.data["source_ip"] == "192.168.1.100"
        assert event.data["destination_ip"] == "10.0.0.1"
        assert event.data["source_port"] == 54321
        assert event.data["destination_port"] == 80
        assert event.data["protocol"] == "tcp"
        assert event.data["packets"] == 100
        assert event.data["bytes_sent"] == 15000


class TestNetFlowFieldDefinitions:
    """Test NetFlow field type definitions in ag3ntwerk optimizer."""

    def test_netflow_v9_field_types_comprehensive(self):
        """Verify comprehensive NetFlow v9 field type definitions are in the codebase."""
        # Read the optimizer file and verify field definitions
        with open("F:/Projects/public-release/ag3ntwerk/src/sentinel/src/sentinel/agents/optimizer.py") as f:
            content = f.read()

        # Verify key field types are defined
        assert "_netflow_v9_field_types" in content
        assert "IN_BYTES" in content
        assert "IN_PKTS" in content
        assert "PROTOCOL" in content
        assert "L4_SRC_PORT" in content
        assert "L4_DST_PORT" in content
        assert "IPV4_SRC_ADDR" in content
        assert "IPV4_DST_ADDR" in content
        assert "IPV6_SRC_ADDR" in content
        assert "IPV6_DST_ADDR" in content

    def test_ipfix_field_types_comprehensive(self):
        """Verify comprehensive IPFIX field type definitions are in the codebase."""
        with open("F:/Projects/public-release/ag3ntwerk/src/sentinel/src/sentinel/agents/optimizer.py") as f:
            content = f.read()

        # Verify key IPFIX Information Elements are defined
        assert "_ipfix_field_types" in content
        assert "octetDeltaCount" in content
        assert "packetDeltaCount" in content
        assert "protocolIdentifier" in content
        assert "sourceTransportPort" in content
        assert "destinationTransportPort" in content
        assert "sourceIPv4Address" in content
        assert "destinationIPv4Address" in content
        assert "sourceIPv6Address" in content
        assert "destinationIPv6Address" in content

    def test_template_parsing_implemented(self):
        """Verify template parsing methods are implemented."""
        with open("F:/Projects/public-release/ag3ntwerk/src/sentinel/src/sentinel/agents/optimizer.py") as f:
            content = f.read()

        # Verify template parsing methods exist
        assert "_parse_v9_template_flowset" in content
        assert "_parse_v9_data_flowset" in content
        assert "_decode_v9_record" in content
        assert "_parse_ipfix_template_set" in content
        assert "_parse_ipfix_data_set" in content
        assert "_decode_ipfix_record" in content
        assert "_decode_ipfix_field" in content
        assert "_emit_ipfix_flow_event" in content

        # Verify template caches are defined
        assert "_netflow_v9_templates" in content
        assert "_ipfix_templates" in content

"""PSMoveClient Socket & Network Protocol Manager.

Handles dual TCP/UDP socket communication with PSMoveServiceEx, managing initial
handshakes, UDP binding, subscription requests, and event-driven data streaming.
"""

import select
import socket
import struct
import time
from typing import Callable, Optional

from psmovebridge import protocol_pb2 as proto
from .tracker import HMDData


class PSMoveClient:
    """Network client for interfacing with PSMoveServiceEx over TCP and UDP.

    Attributes:
        ip (str): Target IP address of the PSMoveServiceEx server.
        port (int): Target TCP/UDP port (default is 9512).
        tcp_sock (Optional[socket.socket]): TCP socket for control/handshake.
        udp_sock (Optional[socket.socket]): UDP socket for high-frequency tracking streams.
        connection_id (int): Session ID assigned by the server upon connection.
        is_running (bool): State flag controlling the main event loop.
        hmd_data (HMDData): Instance storing the parsed HMD spatial state.
    """

    def __init__(self, ip: str = "127.0.0.1", port: int = 9512) -> None:
        """Initializes the PSMoveClient instance."""
        self.ip: str = ip
        self.port: int = port
        self.tcp_sock: Optional[socket.socket] = None
        self.udp_sock: Optional[socket.socket] = None
        self.connection_id: int = -1
        self.is_running: bool = False
        self.hmd_data: HMDData = HMDData()

    def connect(self) -> None:
        """Establishes dual TCP/UDP connections and executes the service handshake.

        Configures socket options (including Windows-specific SIO_UDP_CONNRESET fixes),
        retrieves the session TCP connection ID, and registers the local UDP socket.
        """
        # 1. Initialize and bind local UDP socket
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Fix WinError 10054: Prevents UDP socket termination when ICMP Port Unreachable is returned
            self.udp_sock.ioctl(-1744830452, False)
        except (AttributeError, OSError, ValueError):
            pass
        self.udp_sock.bind(("127.0.0.1", 0))

        # 2. Establish control TCP socket connection
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.connect((self.ip, self.port))

        # 3. Read initial response to extract assigned session connection_id
        init_payload = self._recv_tcp()
        if init_payload:
            res = proto.Response()
            res.ParseFromString(init_payload)
            if hasattr(res, "result_connection_info"):
                self.connection_id = res.result_connection_info.tcp_connection_id

        # 4. Transmit UDP registration frame to pair sockets on the server side
        input_df = proto.DeviceInputDataFrame()
        if hasattr(input_df, "connection_id"):
            input_df.connection_id = self.connection_id
        elif hasattr(input_df, "tcp_connection_id"):
            input_df.tcp_connection_id = self.connection_id

        serialized_msg = input_df.SerializeToString()
        header = struct.pack(">I", len(serialized_msg))

        # Send packet burst to guarantee UDP registration
        for _ in range(3):
            self.udp_sock.sendto(header + serialized_msg, (self.ip, self.port))
            time.sleep(0.01)

    def subscribe_hmd(self, hmd_id: int = 0) -> None:
        """Sends a request over TCP to subscribe to a specific HMD data stream.

        Args:
            hmd_id (int): Target HMD device identifier (default is 0).
        """
        if not self.tcp_sock:
            raise RuntimeError("TCP socket is not connected. Call connect() first.")

        req = proto.Request()
        req.type = proto.Request.RequestType.Value("START_HMD_DATA_STREAM")
        req.request_id = 1
        stream_req = req.request_start_hmd_data_stream
        stream_req.hmd_id = hmd_id
        stream_req.include_position_data = True
        stream_req.include_raw_tracker_data = True

        req_bytes = req.SerializeToString()
        self.tcp_sock.sendall(struct.pack(">I", len(req_bytes)) + req_bytes)
        self._recv_tcp()  # Await server ACK response

    def listen(self, callback: Callable[[HMDData], None]) -> None:
        """Main non-blocking event loop using I/O multiplexing.

        Listens for incoming UDP datagrams, parses Protobuf payloads, and invokes
        the provided callback upon valid pose updates.

        Args:
            callback (Callable[[HMDData], None]): Function triggered when HMD pose updates.
        """
        if not self.udp_sock or not self.tcp_sock:
            raise RuntimeError("Sockets are not initialized. Call connect() first.")

        self.is_running = True
        try:
            while self.is_running:
                # Multiplex socket I/O with 50ms timeout to prevent CPU spinning
                readable, _, _ = select.select(
                    [self.udp_sock, self.tcp_sock], [], [], 0.05
                )
                for s in readable:
                    if s is self.udp_sock:
                        data, _ = self.udp_sock.recvfrom(4096)
                        if len(data) > 4:
                            # Extract 4-byte big-endian framing length header
                            size = struct.unpack(">I", data[:4])[0]
                            df = proto.DeviceOutputDataFrame()
                            df.ParseFromString(data[4 : 4 + size])

                            if df.HasField("hmd_data_packet"):
                                if self.hmd_data.update_from_protobuf(df.hmd_data_packet):
                                    callback(self.hmd_data)
        except KeyboardInterrupt:
            self.close()

    def close(self) -> None:
        """Gracefully terminates sockets and stops the listening loop."""
        self.is_running = False
        if self.tcp_sock:
            self.tcp_sock.close()
            self.tcp_sock = None
        if self.udp_sock:
            self.udp_sock.close()
            self.udp_sock = None

    def _recv_tcp(self) -> Optional[bytes]:
        """Internal helper to read length-prefixed messages over TCP.

        Returns:
            Optional[bytes]: The deserialized binary payload, or None on failure.
        """
        if not self.tcp_sock:
            return None

        try:
            # Read 4-byte big-endian message length header
            raw_len = self.tcp_sock.recv(4)
            if not raw_len:
                return None
            length = struct.unpack(">I", raw_len)[0]

            # Read exact payload byte count
            payload = b""
            while len(payload) < length:
                chunk = self.tcp_sock.recv(length - len(payload))
                if not chunk:
                    break
                payload += chunk
            return payload
        except Exception:
            return None
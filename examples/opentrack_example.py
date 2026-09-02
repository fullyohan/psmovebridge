import socket
import struct
from psmovebridge import PSMoveClient

# UDP socket for OpenTrack (port 4242)
opentrack_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def on_pose_updated(hmd):
    """Callback function triggered on each HMD pose update."""
    pos = hmd.position
    print(f"\rPosition: X={pos.x:.2f}, Y={pos.y:.2f}, Z={pos.z:.2f}", end="")

    # Send 6DoF data to OpenTrack (x, y, z, yaw, pitch, roll)
    payload = struct.pack("dddddd", pos.x, pos.y, pos.z, 0.0, 0.0, 0.0)
    opentrack_sock.sendto(payload, ("127.0.0.1", 4242))


# Initialize and start client
client = PSMoveClient()
client.connect()
client.subscribe_hmd(hmd_id=0)
client.listen(callback=on_pose_updated)
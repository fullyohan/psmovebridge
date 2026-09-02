"""HMD Data Abstraction Module.

Provides data structures and parsing logic for Head-Mounted Display (HMD)
position and orientation data extracted from PSMoveServiceEx Protobuf
packets.
"""

from dataclasses import dataclass


@dataclass
class Position:
    """3D spatial coordinates in centimeters."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class Orientation:
    """3D angular rotation in degrees (Euler angles)."""

    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0


class HMDData:
    """Encapsulates tracking state for an HMD device.

    Parses raw Protobuf HMD packets and updates internal position/orientation
    states with fallback support for standard pose structures.
    """

    def __init__(self):
        self.position = Position()
        self.orientation = Orientation()
        self.raw_packet = None

    def update_from_protobuf(self, hmd_packet) -> bool:
        """Parses an incoming HMD data packet from PSMoveServiceEx.

        Args:
            hmd_packet: The deserialized `hmd_data_packet` Protobuf message.

        Returns:
            bool: True if positional data was successfully updated, False
            otherwise.
        """
        self.raw_packet = hmd_packet

        # Primary extraction path: PSMoveServiceEx virtual HMD state wrapper
        if hasattr(
            hmd_packet, "virtual_hmd_state"
        ) and hmd_packet.HasField("virtual_hmd_state"):
            state = hmd_packet.virtual_hmd_state
            if hasattr(state, "position_cm") and state.HasField("position_cm"):
                self.position.x = state.position_cm.x
                self.position.y = state.position_cm.y
                self.position.z = state.position_cm.z
                return True

        # Fallback path: Standard PSMoveService HMD pose structure
        if hasattr(hmd_packet, "pose") and hmd_packet.HasField("pose"):
            if hasattr(hmd_packet.pose, "position"):
                self.position.x = hmd_packet.pose.position.x
                self.position.y = hmd_packet.pose.position.y
                self.position.z = hmd_packet.pose.position.z
                return True

        return False
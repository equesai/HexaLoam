"""ROS2 Humble/Jazzy bridge for HexaLoam joint_states and cmd_vel."""
from __future__ import annotations

try:
    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import Twist
    from sensor_msgs.msg import JointState
except ImportError:  # pragma: no cover
    rclpy = None
    Node = object  # type: ignore[assignment]

from hexaloam_controller.robot import HexaLoamRobot


class HexaLoamRos2Node(Node):  # type: ignore[misc]
    def __init__(self, mode: str = "single_esp32") -> None:
        super().__init__("hexaloam_controller_node")
        self.robot = HexaLoamRobot(mode=mode)
        self.robot.connect()
        self.robot.arm()
        self.robot.stand()
        self.vx = 0.0
        self.vy = 0.0
        self.wz = 0.0
        self.pub_js = self.create_publisher(JointState, "joint_states", 10)
        self.sub_vel = self.create_subscription(Twist, "cmd_vel", self._on_vel, 10)
        self.timer = self.create_timer(0.02, self._tick)

    def _on_vel(self, msg: Twist) -> None:
        self.vx = float(msg.linear.x)
        self.vy = float(msg.linear.y)
        self.wz = float(msg.angular.z)

    def _tick(self) -> None:
        q = self.robot.move(vx=self.vx, vy=self.vy, wz=self.wz, dt=0.02)
        js = JointState()
        js.header.stamp = self.get_clock().now().to_msg()
        js.name = [j["name"] for j in self.robot.config["joints"]]
        js.position = [float(v) for v in q]
        self.pub_js.publish(js)


def main() -> None:  # pragma: no cover
    if rclpy is None:
        raise RuntimeError("ROS2 rclpy is not installed in this Python environment.")
    rclpy.init()
    node = HexaLoamRos2Node()
    try:
        rclpy.spin(node)
    finally:
        node.robot.disconnect()
        node.destroy_node()
        rclpy.shutdown()

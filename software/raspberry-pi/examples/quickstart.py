"""Quickstart example for HexaLoamRobot (mock, single_esp32, or dual_esp32)."""
from hexaloam_controller.robot import HexaLoamRobot


def main() -> None:
    robot = HexaLoamRobot(mode="mock_single")
    robot.connect()
    robot.validate_configuration()
    robot.arm()
    robot.stand(body_height_m=0.145)
    robot.set_gait("tripod")
    for _ in range(10):
        robot.move(vx=0.03, vy=0.0, wz=0.0)
    robot.set_gait("ripple")
    robot.set_body_height(0.155)
    for _ in range(10):
        robot.move(vx=0.02, vy=0.0, wz=0.0)
    robot.stop()
    robot.sit()
    robot.disarm()
    robot.disconnect()
    print("HexaLoam quickstart completed cleanly.")


if __name__ == "__main__":
    main()

# Verbatim from the Docker guide "Introduction to ROS 2 Development with Docker",
# section "Create a simple publisher" (https://docs.docker.com/guides/ros2/), fetched 2026-09-28.
import time

import rclpy
from geometry_msgs.msg import Twist


def main():
    rclpy.init()
    node = rclpy.create_node("turtle_mover")
    publisher = node.create_publisher(Twist, "turtle1/cmd_vel", 10)

    # Create a twist message
    msg = Twist()
    msg.linear.x = 2.0  # Move forward at 2 m/s
    msg.angular.z = 1.0  # Rotate at 1 rad/s

    # Publish the message
    for i in range(50):
        publisher.publish(msg)
        time.sleep(0.1)

    # Stop the turtle
    msg.linear.x = 0.0
    msg.angular.z = 0.0
    publisher.publish(msg)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

# A minimal launch_testing test: launch the C++ talker and check its output.
import unittest

import launch
import launch_ros.actions
import launch_testing
import launch_testing.actions
import launch_testing.asserts


def generate_test_description():
    talker = launch_ros.actions.Node(package="demo_nodes_cpp", executable="talker", output="screen")
    return launch.LaunchDescription([talker, launch_testing.actions.ReadyToTest()]), {
        "talker": talker
    }


class TestTalkerOutput(unittest.TestCase):
    def test_talker_publishes(self, proc_output, talker):
        proc_output.assertWaitFor("Publishing", process=talker, timeout=60)

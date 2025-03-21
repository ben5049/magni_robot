# ICRSBot Magni Robot

This repository contains all the code that runs on the ICRSBot's onboard Raspberry Pi. You can find the code that runs on the laptop in the [HCR_ICRS_Interaction repo](https://github.com/MITeo21/HCR_ICRS_Interaction).

- The launch files have been heavily modified in [/magni_description](/magni_description) to support our robot configuration.
- The script [ros_impostor_server.py](discord_bridge/ros_impostor_server.py) allows ROS on the Raspberry Pi to communicate with the the interaction running on the laptop.
- The SALMON navigation script is in [/salmon/launch/test.py](/salmon/launch/test.py).
- Other config and launch files relating to navigation are in [/magni_nav](/magni_nav).

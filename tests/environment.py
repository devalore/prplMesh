###############################################################
# SPDX-License-Identifier: BSD-2-Clause-Patent
# Copyright (c) 2020 Arnout Vandecappelle (Essensium/Mind)
# This code is subject to the terms of the BSD+Patent license.
# See LICENSE file for more details.
###############################################################

import os
import re
import subprocess

from capi import UCCSocket
from opts import debug, err, opts, status


class AlEntity:
    '''Abstract representation of a MultiAP device (1905.1 AL Entity).

    Derived classes provide concrete implementations for a specific device (e.g. docker).

    This provides basic information about the entity, e.g. its AL MAC address. How this information
    is retrieved is implementation-specific.

    It also provides an abstract interface to interact with the entity, e.g. for sending CAPI
    commands.

    If a device runs both the agent and the controller, two AlEntities should be created for it,
    with the same MAC address. This is not how it is modeled in 1905.1, but it corresponds to how
    it is implemented in prplMesh and it allows us to have e.g. a separate UCCSocket to controller
    and agent.
    '''
    def __init__(self, mac: str, ucc_socket: UCCSocket, is_controller: bool = False):
        self.mac = mac
        self.ucc_socket = ucc_socket
        self.is_controller = is_controller
        self.radios = []

        # Convenience functions that propagate to ucc_socket
        self.cmd_reply = self.ucc_socket.cmd_reply
        self.dev_get_parameter = self.ucc_socket.dev_get_parameter
        self.dev_send_1905 = self.ucc_socket.dev_send_1905

    def command(self, *command: str) -> bytes:
        '''Run `command` on the device and return its output as bytes.'''
        raise NotImplementedError("command is not implemented in abstract class AlEntity")


class Radio:
    '''Abstract representation of a radio on a MultiAP agent.

    This provides basic information about the radio, e.g. its mac address, and functionality for
    checking its status.
    '''
    def __init__(self, agent: AlEntity, mac: str):
        self.agent = agent
        agent.radios.append(self)
        self.mac = mac


class AlEntityDocker(AlEntity):
    '''Docker implementation of AlEntity.

    The entity is defined from the name of the container, the rest is derived from that.
    '''
    def __init__(self, name: str, is_controller: bool = False):
        self.name = name
        self.rootdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.installdir = os.path.join(self.rootdir, 'build', 'install')
        self.bridge_name = 'br-lan'

        # First, get the UCC port from the config file
        if is_controller:
            config_file_name = 'beerocks_controller.conf'
        else:
            config_file_name = 'beerocks_agent.conf'
        with open(os.path.join(self.installdir, 'config', config_file_name)) as config_file:
            ucc_port = \
                re.search(r'ucc_listener_port=(?P<port>[0-9]+)', config_file.read()).group('port')

        device_ip_output = self.command('ip', '-f', 'inet', 'addr', 'show', self.bridge_name)
        device_ip = re.search(r'inet (?P<ip>[0-9.]+)', device_ip_output.decode('utf-8')).group('ip')

        ucc_socket = UCCSocket(device_ip, ucc_port)
        mac = ucc_socket.dev_get_parameter('ALid')

        super().__init__(mac, ucc_socket, is_controller)

        # We always have two radios, wlan0 and wlan2
        RadioDocker(self, "wlan0")
        RadioDocker(self, "wlan2")

    def command(self, *command: str) -> bytes:
        '''Execute `command` in docker container and return its output.'''
        return subprocess.check_output(("docker", "exec", self.name) + command)


class RadioDocker(Radio):
    '''Docker implementation of a radio.'''
    def __init__(self, agent: AlEntityDocker, iface_name: str):
        self.iface_name = iface_name
        ip_output = agent.command("ip", "-o",  "link", "list", "dev", "wlan0")
        mac = re.search(rb"link/ether (([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})", ip_output).group(1).decode()
        super().__init__(agent, mac)


class TestEnvironment:
    '''Specification of the test environment.

    This is allows access to the interfaces of the test environment. It is created as a singleton
    object that is populated with implementations of the abstract classes defining the different
    components.
    '''
    def __init__(self, sniffer_interface: str):
        self.sniffer_interface = sniffer_interface
        self.tcpdump_proc = None

    def tcpdump_start(self, outputfile):
        '''Start tcpdump if enabled by config.'''
        if opts.tcpdump:
            debug("Starting tcpdump, output file {}".format(outputfile))
            command = ["tcpdump", "-i", self.sniffer_interface, "-w", outputfile]
            self.tcpdump_proc = subprocess.Popen(command, stderr=subprocess.PIPE)
            # tcpdump takes a while to start up. Wait for the appropriate output before continuing.
            # poll() so we exit the loop if tcpdump terminates for any reason.
            while not self.tcpdump_proc.poll():
                line = self.tcpdump_proc.stderr.readline()
                debug(line.decode()[:-1])  # strip off newline
                if line.startswith(b"tcpdump: listening on " + self.sniffer_interface.encode()):
                    # Make sure it doesn't block due to stderr buffering
                    self.tcpdump_proc.stderr.close()
                    break
            else:
                err("tcpdump terminated")
                self.tcpdump_proc = None

    def tcpdump_kill(self):
        '''Stop tcpdump if it is running.'''
        if self.tcpdump_proc:
            status("Terminating tcpdump")
            self.tcpdump_proc.terminate()
            self.tcpdump_proc = None


environment = None

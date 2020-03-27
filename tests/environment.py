###############################################################
# SPDX-License-Identifier: BSD-2-Clause-Patent
# Copyright (c) 2020 Arnout Vandecappelle (Essensium/Mind)
# This code is subject to the terms of the BSD+Patent license.
# See LICENSE file for more details.
###############################################################

import json
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


class Sniffer:
    '''Captures packets on an interface.'''
    def __init__(self, interface: str):
        self.interface = interface
        self.tcpdump_proc = None

    def start(self, outputfile_basename):
        '''Start tcpdump if enabled by config.'''
        if opts.tcpdump:
            debug("Starting tcpdump, output file {}.pcap".format(outputfile_basename))
            outputfile = os.path.join(opts.tcpdump_dir, outputfile_basename) + ".pcap"
            command = ["tcpdump", "-i", self.interface, "-w", outputfile]
            self.tcpdump_proc = subprocess.Popen(command, stderr=subprocess.PIPE)
            # tcpdump takes a while to start up. Wait for the appropriate output before continuing.
            # poll() so we exit the loop if tcpdump terminates for any reason.
            while not self.tcpdump_proc.poll():
                line = self.tcpdump_proc.stderr.readline()
                debug(line.decode()[:-1])  # strip off newline
                if line.startswith(b"tcpdump: listening on " + self.interface.encode()):
                    # Make sure it doesn't block due to stderr buffering
                    self.tcpdump_proc.stderr.close()
                    break
            else:
                err("tcpdump terminated")
                self.tcpdump_proc = None

    def stop(self):
        '''Stop tcpdump if it is running.'''
        if self.tcpdump_proc:
            status("Terminating tcpdump")
            self.tcpdump_proc.terminate()
            self.tcpdump_proc = None

# The following variables are initialized as None, and have to be set when a concrete test
# environment is started.
wired_sniffer = None
controller = None
agents = []


# Concrete implementation with docker

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


def launch_environment_docker(unique_id: str, skip_init: bool = False):
    docker_network = 'prplMesh-net-{}'.format(unique_id)
    docker_network_inspect_cmd = ('docker', 'network', 'inspect', docker_network)
    inspect_result = subprocess.run(docker_network_inspect_cmd, stdout=subprocess.PIPE)
    if inspect_result.returncode != 0:
        # Assume network doesn't exist yet. Create it.
        # This is normally done by test_gw_repeater.sh, but we need it earlier to be able to start
        # tcpdump
        # Raise an exception if it fails.
        subprocess.run(('docker', 'network', 'create', docker_network), check=True,
                        stdout=subprocess.DEVNULL)
        # Inspect again, now raise if it fails.
        inspect_result = subprocess.run(docker_network_inspect_cmd, check=True,
                                        stdout=subprocess.PIPE)

    inspect = json.loads(inspect_result.stdout)
    prplmesh_net = inspect[0]
    # podman adds a 'plugins' indirection that docker doesn't have.
    if 'plugins' in prplmesh_net:
        bridge = prplmesh_net['plugins'][0]['bridge']
    else:
        # docker doesn't report the interface name of the bridge. So format it based on the ID.
        bridge_id = prplmesh_net['Id']
        bridge = 'br-' + bridge_id[:12]

    global wired_sniffer
    wired_sniffer = Sniffer(bridge)

    if not skip_init:
        wired_sniffer.start('init')
        try:
            subprocess.check_call((os.path.join(self.rootdir, "tests", "test_gw_repeater.sh"),
                                    "-f", "-u", unique_id, "-g", self.gateway,
                                    "-r", self.repeater1, "-r", self.repeater2, "-d", "7"))
        finally:
            wired_sniffer.stop()

    global controller, agents
    controller = AlEntityDocker('gateway-' + unique_id, True)
    agents = (AlEntityDocker('repeater1-' + unique_id), AlEntityDocker('repeater2-' + unique_id))

    debug('controller: {}'.format(controller.mac))
    debug('agent1: {}'.format(agents[0].mac))
    debug('agent1 wlan0: {}'.format(agents[0].radios[0].mac))
    debug('agent1 wlan2: {}'.format(agents[0].radios[1].mac))
    debug('agent2: {}'.format(agents[1].mac))
    debug('agent2 wlan0: {}'.format(agents[1].radios[0].mac))
    debug('agent2 wlan2: {}'.format(agents[1].radios[1].mac))

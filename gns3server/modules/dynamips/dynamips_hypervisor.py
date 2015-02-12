# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 GNS3 Technologies Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Interface for Dynamips hypervisor management module ("hypervisor")
http://github.com/GNS3/dynamips/blob/master/README.hypervisor#L46
"""

import socket
import re
import logging
import asyncio

from .dynamips_error import DynamipsError
from .nios.nio_udp_auto import NIOUDPAuto

log = logging.getLogger(__name__)


class DynamipsHypervisor:
    """
    Creates a new connection to a Dynamips server (also called hypervisor)

    :param working_dir: working directory
    :param host: the hostname or ip address string of the Dynamips server
    :param port: the tcp port integer (defaults to 7200)
    :param timeout: timeout integer for how long to wait for a response to commands sent to the
    hypervisor (defaults to 30 seconds)
    """

    # Used to parse Dynamips response codes
    error_re = re.compile(r"""^2[0-9]{2}-""")
    success_re = re.compile(r"""^1[0-9]{2}\s{1}""")

    def __init__(self, working_dir, host, port=7200, timeout=30.0):

        self._host = host
        self._port = port

        self._devices = []
        self._ghosts = {}
        self._jitsharing_groups = {}
        self._working_dir = working_dir
        # self._console_start_port_range = 2001
        # self._console_end_port_range = 2500
        # self._aux_start_port_range = 2501
        # self._aux_end_port_range = 3000
        # self._udp_start_port_range = 10001
        # self._udp_end_port_range = 20000
        self._nio_udp_auto_instances = {}
        self._version = "N/A"
        self._timeout = timeout
        self._uuid = None
        self._reader = None
        self._writer = None

    @asyncio.coroutine
    def connect(self):
        """
        Connects to the hypervisor.
        """

        # connect to a local address by default
        # if listening to all addresses (IPv4 or IPv6)
        if self._host == "0.0.0.0":
            host = "127.0.0.1"
        elif self._host == "::":
            host = "::1"
        else:
            host = self._host

        try:
            self._reader, self._writer = yield from asyncio.wait_for(asyncio.open_connection(host, self._port), timeout=self._timeout)
        except OSError as e:
            raise DynamipsError("Could not connect to hypervisor {}:{} {}".format(host, self._port, e))
        except asyncio.TimeoutError:
            raise DynamipsError("Timeout error while connecting to hypervisor {}:{}".format(host, self._port))

        try:
            version = yield from self.send("hypervisor version")
            self._version = version[0].split("-", 1)[0]
        except IndexError:
            self._version = "Unknown"

        self._uuid = yield from self.send("hypervisor uuid")

        # this forces to send the working dir to Dynamips
        yield from self.set_working_dir(self._working_dir)

    @property
    def version(self):
        """
        Returns Dynamips version.

        :returns: version string
        """

        return self._version

    @asyncio.coroutine
    def close(self):
        """
        Closes the connection to this hypervisor (but leave it running).
        """

        yield from self.send("hypervisor close")
        self._writer.close()
        self._reader, self._writer = None

    @asyncio.coroutine
    def stop(self):
        """
        Stops this hypervisor (will no longer run).
        """

        yield from self.send("hypervisor stop")
        self._writer.close()
        self._reader, self._writer = None
        self._nio_udp_auto_instances.clear()

    @asyncio.coroutine
    def reset(self):
        """
        Resets this hypervisor (used to get an empty configuration).
        """

        yield from self.send("hypervisor reset")
        self._nio_udp_auto_instances.clear()

    @asyncio.coroutine
    def set_working_dir(self, working_dir):
        """
        Sets the working directory for this hypervisor.

        :param working_dir: path to the working directory
        """

        # encase working_dir in quotes to protect spaces in the path
        yield from self.send("hypervisor working_dir {}".format('"' + working_dir + '"'))
        self._working_dir = working_dir
        log.debug("Working directory set to {}".format(self._working_dir))

    @property
    def working_dir(self):
        """
        Returns current working directory

        :returns: path to the working directory
        """

        return self._working_dir

    @property
    def uuid(self):
        """
        Returns this hypervisor UUID.

        :Returns: uuid string
        """

        return self._uuid

    @property
    def devices(self):
        """
        Returns the list of devices managed by this hypervisor instance.

        :returns: a list of device instances
        """

        return self._devices

    # @devices.setter
    # def devices(self, devices):
    #     """
    #     Sets the list of devices managed by this hypervisor instance.
    #     This method is for internal use.
    #
    #     :param devices: a list of device objects
    #     """
    #
    #     self._devices = devices

    # @property
    # def console_start_port_range(self):
    #     """
    #     Returns the console start port range value
    #
    #     :returns: console start port range value (integer)
    #     """
    #
    #     return self._console_start_port_range

    # @console_start_port_range.setter
    # def console_start_port_range(self, console_start_port_range):
    #     """
    #     Set a new console start port range value
    #
    #     :param console_start_port_range: console start port range value (integer)
    #     """
    #
    #     self._console_start_port_range = console_start_port_range
    #
    # @property
    # def console_end_port_range(self):
    #     """
    #     Returns the console end port range value
    #
    #     :returns: console end port range value (integer)
    #     """
    #
    #     return self._console_end_port_range
    #
    # @console_end_port_range.setter
    # def console_end_port_range(self, console_end_port_range):
    #     """
    #     Set a new console end port range value
    #
    #     :param console_end_port_range: console end port range value (integer)
    #     """
    #
    #     self._console_end_port_range = console_end_port_range

    # @property
    # def aux_start_port_range(self):
    #     """
    #     Returns the auxiliary console start port range value
    #
    #     :returns: auxiliary console  start port range value (integer)
    #     """
    #
    #     return self._aux_start_port_range
    #
    # @aux_start_port_range.setter
    # def aux_start_port_range(self, aux_start_port_range):
    #     """
    #     Sets a new auxiliary console start port range value
    #
    #     :param aux_start_port_range: auxiliary console start port range value (integer)
    #     """
    #
    #     self._aux_start_port_range = aux_start_port_range
    #
    # @property
    # def aux_end_port_range(self):
    #     """
    #     Returns the auxiliary console end port range value
    #
    #     :returns: auxiliary console end port range value (integer)
    #     """
    #
    #     return self._aux_end_port_range
    #
    # @aux_end_port_range.setter
    # def aux_end_port_range(self, aux_end_port_range):
    #     """
    #     Sets a new auxiliary console end port range value
    #
    #     :param aux_end_port_range: auxiliary console end port range value (integer)
    #     """
    #
    #     self._aux_end_port_range = aux_end_port_range

    # @property
    # def udp_start_port_range(self):
    #     """
    #     Returns the UDP start port range value
    #
    #     :returns: UDP start port range value (integer)
    #     """
    #
    #     return self._udp_start_port_range
    #
    # @udp_start_port_range.setter
    # def udp_start_port_range(self, udp_start_port_range):
    #     """
    #     Sets a new UDP start port range value
    #
    #     :param udp_start_port_range: UDP start port range value (integer)
    #     """
    #
    #     self._udp_start_port_range = udp_start_port_range
    #
    # @property
    # def udp_end_port_range(self):
    #     """
    #     Returns the UDP end port range value
    #
    #     :returns: UDP end port range value (integer)
    #     """
    #
    #     return self._udp_end_port_range
    #
    # @udp_end_port_range.setter
    # def udp_end_port_range(self, udp_end_port_range):
    #     """
    #     Sets an new UDP end port range value
    #
    #     :param udp_end_port_range: UDP end port range value (integer)
    #     """
    #
    #     self._udp_end_port_range = udp_end_port_range

    @property
    def ghosts(self):
        """
        Returns a list of the ghosts hosted by this hypervisor.

        :returns: Ghosts dict (image_name -> device)
        """

        return self._ghosts

    def add_ghost(self, image_name, router):
        """
        Adds a ghost name to the list of ghosts created on this hypervisor.

        :param image_name: name of the ghost image
        :param router: Router instance
        """

        self._ghosts[image_name] = router

    @property
    def jitsharing_groups(self):
        """
        Returns a list of the JIT sharing groups hosted by this hypervisor.

        :returns: JIT sharing groups dict (image_name -> group number)
        """

        return self._jitsharing_groups

    def add_jitsharing_group(self, image_name, group_number):
        """
        Adds a JIT blocks sharing group name to the list of groups created on this hypervisor.

        :param image_name: name of the ghost image
        :param group_number: group (integer)
        """

        self._jitsharing_groups[image_name] = group_number

    @property
    def port(self):
        """
        Returns the port used to start the hypervisor.

        :returns: port number (integer)
        """

        return self._port

    @port.setter
    def port(self, port):
        """
        Sets the port used to start the hypervisor.

        :param port: port number (integer)
        """

        self._port = port

    @property
    def host(self):
        """
        Returns the host (binding) used to start the hypervisor.

        :returns: host/address (string)
        """

        return self._host

    @host.setter
    def host(self, host):
        """
        Sets the host (binding) used to start the hypervisor.

        :param host: host/address (string)
        """

        self._host = host

    def get_nio_udp_auto(self, port):
        """
        Returns an allocated NIO UDP auto instance.

        :returns: NIO UDP auto instance
        """

        if port in self._nio_udp_auto_instances:
            return self._nio_udp_auto_instances.pop(port)
        else:
            return None

    def allocate_udp_port(self):
        """
        Allocates a new UDP port for creating an UDP NIO Auto.

        :returns: port number (integer)
        """

        # use Dynamips's NIO UDP auto back-end.
        nio = NIOUDPAuto(self, self._host, self._udp_start_port_range, self._udp_end_port_range)
        self._nio_udp_auto_instances[nio.lport] = nio
        allocated_port = nio.lport
        return allocated_port

    @asyncio.coroutine
    def send(self, command):
        """
        Sends commands to this hypervisor.

        :param command: a Dynamips hypervisor command

        :returns: results as a list
        """

        # Dynamips responses are of the form:
        #   1xx yyyyyy\r\n
        #   1xx yyyyyy\r\n
        #   ...
        #   100-yyyy\r\n
        # or
        #   2xx-yyyy\r\n
        #
        # Where 1xx is a code from 100-199 for a success or 200-299 for an error
        # The result might be multiple lines and might be less than the buffer size
        # but still have more data. The only thing we know for sure is the last line
        # will begin with '100-' or a '2xx-' and end with '\r\n'

        if self._writer is None or self._reader is None:
            raise DynamipsError("Not connected")

        try:
            command = command.strip() + '\n'
            log.debug("sending {}".format(command))
            self._writer.write(command.encode())
        except OSError as e:
            raise DynamipsError("Lost communication with {host}:{port} :{error}, Dynamips process running: {run}"
                                .format(host=self._host, port=self._port, error=e, run=self.is_running()))

        # Now retrieve the result
        data = []
        buf = ''
        while True:
            try:
                chunk = yield from self._reader.read(1024)  # match to Dynamips' buffer size
                buf += chunk.decode()
            except OSError as e:
                raise DynamipsError("Communication timed out with {host}:{port} :{error}, Dynamips process running: {run}"
                                    .format(host=self._host, port=self._port, error=e, run=self.is_running()))

            # If the buffer doesn't end in '\n' then we can't be done
            try:
                if buf[-1] != '\n':
                    continue
            except IndexError:
                raise DynamipsError("Could not communicate with {host}:{port}, Dynamips process running: {run}"
                                    .format(host=self._host, port=self._port, run=self.is_running()))

            data += buf.split('\r\n')
            if data[-1] == '':
                data.pop()
            buf = ''

            if len(data) == 0:
                raise DynamipsError("no data returned from {host}:{port}, Dynamips process running: {run}"
                                    .format(host=self._host, port=self._port, run=self.is_running()))

            # Does it contain an error code?
            if self.error_re.search(data[-1]):
                raise DynamipsError(data[-1][4:])

            # Or does the last line begin with '100-'? Then we are done!
            if data[-1][:4] == '100-':
                data[-1] = data[-1][4:]
                if data[-1] == 'OK':
                    data.pop()
                break

        # Remove success responses codes
        for index in range(len(data)):
            if self.success_re.search(data[index]):
                data[index] = data[index][4:]

        log.debug("returned result {}".format(data))
        return data

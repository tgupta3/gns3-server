# -*- coding: utf-8 -*-
#
# Copyright (C) 2013 GNS3 Technologies Inc.
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
Interface for multicast NIOs.
"""

import asyncio
from .nio import NIO

import logging
log = logging.getLogger(__name__)


class NIOMcast(NIO):
    """
    Dynamips Linux Ethernet NIO.

    :param hypervisor: Dynamips hypervisor instance
    :param group: multicast group to bind
    :param port: port for binding
    """

    _instance_count = 0

    def __init__(self, hypervisor, group, port):

        NIO.__init__(self, hypervisor)

        # create an unique ID
        self._id = NIOMcast._instance_count
        NIOMcast._instance_count += 1
        self._name = 'nio_mcast' + str(self._id)
        self._group = group
        self._port = port
        self._ttl = 1  # default TTL

    @classmethod
    def reset(cls):
        """
        Reset the instance count.
        """

        cls._instance_count = 0

    @asyncio.coroutine
    def create(self):

        yield from self._hypervisor.send("nio create_mcast {name} {mgroup} {mport}".format(name=self._name,
                                                                                           mgroup=self._group,
                                                                                           mport=self._port))

        log.info("NIO Multicast {name} created with mgroup={group}, mport={port}".format(name=self._name,
                                                                                         group=self._group,
                                                                                         port=self._port))

    @property
    def group(self):
        """
        Returns the multicast group

        :returns: multicast group address
        """

        return self._group

    @property
    def port(self):
        """
        Returns the port

        :returns: port number
        """

        return self._port

    @property
    def ttl(self):
        """
        Returns the TTL associated with the multicast address.

        :returns: TTL value
        """

        return self._ttl

    def set_ttl(self, ttl):
        """
        Sets the TTL for the multicast address

        :param ttl: TTL value
        """

        yield from self._hypervisor.send("nio set_mcast_ttl {name} {ttl}".format(name=self._name,
                                                                                 ttl=ttl))
        self._ttl = ttl

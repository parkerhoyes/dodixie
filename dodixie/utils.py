# License for the Dodixie project, originally found here:
# https://github.com/parkerhoyes/dodixie
#
# Copyright (C) 2017 Parker Hoyes <contact@parkerhoyes.com>
#
# This software is provided "as-is", without any express or implied warranty. In
# no event will the authors be held liable for any damages arising from the use of
# this software.
#
# Permission is granted to anyone to use this software for any purpose, including
# commercial applications, and to alter it and redistribute it freely, subject to
# the following restrictions:
#
# 1. The origin of this software must not be misrepresented; you must not claim
#    that you wrote the original software. If you use this software in a product,
#    an acknowledgment in the product documentation would be appreciated but is
#    not required.
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.

import calendar
import math
import time

from . import api

__all__ = [
    'format_timestamp',
    'parse_timestamp',
    'user_confirm',
    'log',
    'ObjectInfo',
    'IntRanges',
    'Graph'
]

def format_timestamp(secs):
    """Format a UNIX timestamp using ISO 8601 format.

    Args:
        secs: the number of seconds since the Epoch to convert into a timestamp
    Returns:
        an ISO 8601 compliant timestamp of the form "yyyy-mm-ddThh:mm:ssZ"
    """
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(secs))

def parse_timestamp(timestamp):
    """Parse a timestamp of the form "yyyy-mm-ddThh:mm:ssZ".

    Args:
        timestamp: the timestamp, as a string
    Returns:
        the number of seconds since the UNIX Epoch, as described by the timestamp
    """
    return calendar.timegm(time.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ"))

def user_confirm(symbol, prompt):
    """Ask the user for yes / no confirmation using the console.

    Returns:
        True if the user responds yes, or False if the user responds no
    """
    prefix = "[$" + symbol + " " * (3 - len(symbol)) + "] " + prompt + " [Y/n] "
    while True:
        result = input(prefix).strip().lower()
        if result == "y" or result == "yes":
            return True
        if result == "n" or result == "no":
            return False

def log(symbol, message):
    trailing_lf = message.endswith("\n")
    if trailing_lf:
        message = message[:-1]
    prefix = "[" + symbol + " " * (4 - len(symbol)) + "] "
    message = prefix + message.replace("\n", "\n" + prefix)
    if trailing_lf:
        message += "\n"
    print(message, end="")

class ObjectInfo:
    """A representation of an object useful to a human that contains a name for the object and some key-value pairs.

    Args:
        name: a name for the object which should be the object's class's qualified name in most cases"""
    def __init__(self, name):
        self.name = name
        self.info = []
        pass
    def add_info(self, key, value):
        """Add some information about the object.

        Args:
            key: the name to use when displaying this info, as a string
            value: the value of the info as a string, an ObjectInfo object, or a callable that will result in a valid
                   value for this parameter or raise an InsufficientInformationError
        """

        self.info.append((key, value))
    def format_multiline(self):
        """Generate a multiline string representation of this object."""

        s = "<" + self.name + ">\n"
        if len(self.info) == 0:
            return s
        s += ObjectInfo._format_multiline(self.info, 1)
        return s
    def _format_multiline(info, indent):
        s = ""
        for key, value in info:
            s += "    " * indent + key + ": "
            while not isinstance(value, str) and not isinstance(value, ObjectInfo):
                try:
                    value = value()
                except api.InsufficientInformationError:
                    value = "<?>"
            if isinstance(value, str):
                s += value + "\n"
            else:
                s += "<" + value.name + ">\n"
                s += ObjectInfo._format_multiline(self.info, indent + 1)
        return s

class IntRanges:
    def __init__(self, *ranges):
        self._ranges = []
        for r in ranges:
            self.add_range(r[0], r[1])
    def add_range(self, start, end):
        to_remove = []
        for i in range(len(self._ranges)):
            if start <= self._ranges[i][0] and end >= self._ranges[i][1]:
                to_remove.append(i)
        to_remove.reverse()
        for i in to_remove:
            del self._ranges[i]
        del to_remove
        for i in range(len(self._ranges)):
            if start <= self._ranges[i][1]:
                start = self._ranges[i][0]
                del self._ranges[i]
                break
        for i in range(len(self._ranges)):
            if end >= self._ranges[i][0]:
                end = self._ranges[i][1]
                del self._ranges[i]
                break
        self._ranges.append((start, end))
    def includes(self, i):
        for r in self._ranges:
            if r[0] <= i <= r[1]:
                return True
        return False
    def includes_range(self, start, end):
        for r in self._ranges:
            if start >= r[0] and end <= r[1]:
                return True
        return False

class NoSuchPath(Exception):
    pass

class Graph:
    def __init__(self):
        self._nodes = set()
        self._edges = set()
    def add_node(self, node):
        self._nodes.add(node)
    def add_edge(self, node_a, node_b, length=1):
        self._edges.add((node_a, node_b, length))
    def has_node(self, node):
        return node in self._nodes
    def neighbors(self, node):
        for edge in self._edges:
            if edge[0] == node:
                yield edge[1], edge[2]
            elif edge[1] == node:
                yield edge[0], edge[2]
    def shortest_path(self, source, dest):
        """Use an implementation of Dijkstra's algorithm to find the shortest path between two nodes in this graph. This
        method is deterministic.

        Args:
            source: the source node
            dest: the destination node
        Returns:
            a list representing one of the shortest paths from source to dest, the first element being source and the
            last element being dest
        """
        unvisited = self._nodes.copy()
        dist = {}
        for node in self._nodes:
            dist[node] = math.inf
        prev = {}
        dist[source] = 0
        while True:
            current = min(unvisited, key=lambda n: (dist[n], hash(n)))
            if dist[current] == math.inf:
                raise NoSuchPath()
            unvisited.remove(current)
            for neighbor, length in self.neighbors(current):
                if neighbor not in unvisited:
                    continue
                tentative = dist[current] + length
                if tentative < dist[neighbor]:
                    dist[neighbor] = tentative
                    prev[neighbor] = current
            if current == dest:
                break
        del unvisited
        del dist
        path = []
        current = dest
        while True:
            path.append(current)
            if current == source:
                break
            current = prev[current]
        path.reverse()
        return path

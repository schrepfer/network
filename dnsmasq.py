#!/usr/bin/env python3

"""Program intended to help parsing dnsmasq.log files."""

import argparse
import logging
import os
import re
import sys

from dataclasses import dataclass
from typing import Optional

def define_flags() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  # See: http://docs.python.org/3/library/argparse.html
  parser.add_argument(
      '-v', '--verbosity',
      action='store',
      default=logging.WARNING,
      type=int,
      help='the logging verbosity',
      metavar='LEVEL')
  parser.add_argument(
      '-V', '--version',
      action='version',
      version='dnsmasq version 0.1')
  parser.add_argument(
      '--config', '-f',
      type=str,
      help='path to the config file',
      metavar='PATH')
  parser.add_argument(
      '--log', '-l',
      type=str,
      default='/var/log/dnsmasq.log',
      help='path to the dnsmasq.log',
      metavar='LOG')

  args = parser.parse_args()
  check_flags(parser, args)
  return args


def check_flags(parser: argparse.ArgumentParser,
                args: argparse.Namespace) -> None:
  # See: http://docs.python.org/3/library/argparse.html#exiting-methods
  if not os.path.exists(args.log):
    parser.error(f'{args.log} does not exist')

  if not os.path.exists(args.config):
    parser.error(f'{args.config} does not exist')

  return None

BASE_RE = re.compile(
    r'^(?P<datetime>[A-Z][a-z]{2}\s+\d+\s\d{2}:\d{2}:\d{2})'
    r'\s+'
    r'dnsmasq-dhcp\[\d+\]:'
    r'\s+'
    r'(?P<session>\d+)'
    r'\s+'
    r'(?P<message>.*)$'
)

DISCOVER_RE = re.compile(
    r'^DHCPDISCOVER\((?P<interface>[^)]+)\)'
    r'\s+'
    r'(?P<hardware>[0-9a-f]{2}(?::[0-9a-f]{2}){5})'
    r'\s*$'
)

OFFER_RE = re.compile(
    r'^DHCPOFFER\((?P<interface>[^)]+)\)'
    r'\s+'
    r'(?P<ip>[0-9]{1,3}(?:[.][0-9]{1,3}){3})'
    r'\s+'
    r'(?P<hardware>[0-9a-f]{2}(?::[0-9a-f]{2}){5})'
    r'\s*$'
)

CLIENT_NAME_RE = re.compile(
    r'^client provides name: (?P<name>.+)$'
)

VENDOR_CLASS_RE = re.compile(
    r'vendor class: (?P<vendor>.*)$'
)


@dataclass
class DHCP:
  session: int
  index: int
  interface: Optional[str] = None
  hardware: Optional[str] = None
  ip: Optional[str] = None
  name: Optional[str] = None
  vendor: Optional[str] = None


def main(args: argparse.Namespace) -> int:
  entries: dict[int, DHCP] = {}
  with open(args.log) as fh:
    for i, line in enumerate(fh):
      if m := BASE_RE.match(line):
        session = int(m.group('session'))
        entry = entries.setdefault(session, DHCP(session=session, index=i))

        message = m.group('message')
        if n := DISCOVER_RE.match(message):
          entry.interface = n.group('interface')
          entry.hardware = n.group('hardware')
        if n := OFFER_RE.match(message):
          entry.interface = n.group('interface')
          entry.ip = n.group('ip')
          entry.hardware = n.group('hardware')
        if n := CLIENT_NAME_RE.match(message):
          entry.name = n.group('name')
        if n := VENDOR_CLASS_RE.match(message):
          entry.vendor = n.group('vendor')
        
  hardwares: dict[str, DHCP] = {}
  for entry in entries.values():
    if not entry.hardware:
      continue
    if entry.hardware in hardwares:
      if entry.index < hardwares[entry.hardware].index:
        continue
    hardwares[entry.hardware] = entry

  for _, entry in sorted(hardwares.items(), key=lambda x: x[1].hardware):
    print(entry) 

  return os.EX_OK


if __name__ == '__main__':
  a = define_flags()
  logging.basicConfig(
      level=a.verbosity,
      datefmt='%Y/%m/%d %H:%M:%S',
      format='[%(asctime)s] %(levelname)s: %(message)s')
  sys.exit(main(a))
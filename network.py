#!/usr/bin/env python3

"""Generate network configurations."""

import argparse
import difflib
import ipaddress
import logging
import os
import pprint
import re
import sys
import time
import yaml

from django import template
from django.template.loader import render_to_string
from django.conf import settings

from typing import Any, Union


TEMPLATES = {
  'etc/bind/db.0.0.0.0.tmpl': 'etc/bind/db.{{ network_|call:"network" }}',
  'etc/bind/db.domain.tmpl': 'etc/bind/db.{{ domain }}',
  'etc/bind/named.conf.local.tmpl': 'etc/bind/named.conf.local',
  'etc/dhcp/dhcpd.conf.tmpl': 'etc/dhcp/dhcpd.conf',
  'etc/dnsmasq.conf.tmpl': 'etc/dnsmasq.conf',
  'etc/hosts.tmpl': 'etc/hosts',
  'etc/resolv.conf.tmpl': 'etc/resolv.conf',
  'var/www/html/index.html.tmpl': 'var/www/html/index.html',
}


def define_flags() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  # See: http://docs.python.org/3/library/argparse.html
  parser.add_argument(
      '-v', '--verbosity',
      action='store',
      default=20,
      type=int,
      help='the logging verbosity',
      metavar='LEVEL')
  parser.add_argument(
      '--root', '-r',
      type=str,
      default='/',
      help='the output root; where the files end up',
      metavar='DIR')
  parser.add_argument(
      '--print', '-p',
      action='store_true',
      default=False,
      help='print the configuration only')
  parser.add_argument(
      '--diff', '-d',
      action='store_true',
      default=False,
      help='diff the output only')
  parser.add_argument(
      '--templates', '-t',
      nargs=1,
      type=str,
      default=os.path.join(os.path.dirname(__file__), 'templates'),
      help='path where the templates live',
      metavar='DIR')
  parser.add_argument(
      '--config', '-f',
      nargs=1,
      type=str,
      help='path to the config file',
      metavar='PATH')
  parser.add_argument(
      '-V', '--version',
      action='version',
      version='tt version 0.1')

  args = parser.parse_args()
  check_flags(parser, args)
  return args


class Error(Exception):
  def __init__(self, msg, *args):
    super().__init__(msg % args)


class IPv4Address(ipaddress.IPv4Address):
  """IPv4Address with or/and operations."""

  def __init__(self, address: Union[int, str], prefixlen: int = 0):
    super().__init__(address)
    self.prefixlen = prefixlen

  @property
  def reverse_pointer(self) -> str:
    if self.prefixlen and self.prefixlen % 8 == 0:
      dots = self.prefixlen // 8
      reverse_octets = self.octets[:dots-1:-1]
      return '.'.join(map(str, reverse_octets))
    return super().reverse_pointer + '.'

  @property
  def octets(self) -> tuple[int, ...]:
    return tuple((int(self) & 0xff << (i*8)) >> i*8 for i in [3, 2, 1, 0])


class IPv4Network(ipaddress.IPv4Network):
  """IPv4Network."""

  def _address_class(self, address: str) -> IPv4Address:
    return IPv4Address(address, prefixlen=self.prefixlen)

  @property
  def reverse_pointer(self) -> str:
    octets = str(self.network_address).split('.')
    if self.prefixlen % 8 == 0:
      dots = self.prefixlen // 8
      reverse_octets = octets[dots-1::-1]
    else:
      reverse_octets = octets[::-1]
    return '.'.join(reverse_octets) + '.in-addr.arpa'

  @property
  def network(self) -> str:
    octets = str(self.network_address).split('.')
    if self.prefixlen % 8 == 0:
      dots = self.prefixlen // 8
      octets = octets[:dots]
    return '.'.join(octets)

  def __getitem__(self, n: Union[int, str]) -> ipaddress.IPv4Address:
    if isinstance(n, str):
      n = int(self._address_class(n))
    return super().__getitem__(n)

  @property
  def octets(self) -> tuple[int, ...]:
    return tuple((int(self.network_address) & 0xff << (i*8)) >> i*8 for i in [3, 2, 1, 0])


def check_flags(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
  # See: http://docs.python.org/2/library/argparse.html#exiting-methods
  return None


def load_yaml(f: str) -> Any:
  with open(f) as fh:
    return yaml.load(fh, Loader=yaml.CLoader)


mac_pattern = re.compile(r'^[0-9a-f]{2}(:[0-9a-f]{2}){5}$')

def normalize(mac: str) -> str:
  ret = ':'.join(re.findall(r'([0-9a-f]{2})',
    mac.lower().replace('-', '').replace(':', '')))
  assert mac_pattern.match(ret), (
      'mac address "{0}" => "{1}" not matching {2}'.format(mac, ret, mac_pattern))
  return ret

def main(args: argparse.Namespace) -> int:
  if not args.config:
    return 1

  if not args.templates:
    return 1

  if not args.root:
    return 1

  tmp = '/tmp/network-%d' % os.getuid()
  y = load_yaml(args.config[0])
  y['time'] = int(time.time())

  pp = pprint.PrettyPrinter(indent=1)
  pp.pprint(y)

  y['hosts'] = sorted(y['hosts'], key=lambda x: tuple(x.get('ip').split('.')))

  for host in y['hosts']:
    if 'hardware' in host:
      host['hardware'] = normalize(host['hardware'])

  network = IPv4Network(y['network'])

  y.update({
    'network_': network,
    'dynamic_': [
      IPv4Address(ip, prefixlen=network.prefixlen)
      for ip in range(int(network[y['dynamic']['start']]),
                      int(network[y['dynamic']['end']]) + 1)
    ],
  })

  settings.configure(DEBUG=True)
  ctx = template.Context(y)
  register = template.Library()
  register.filter('network', lambda vv: [network[v] for v in vv])
  register.filter('format', lambda v, fmt: v.format(fmt))
  register.filter('addr', lambda v, ip: v[ip])
  register.filter('call', lambda v, attr: getattr(v, attr))
  register.filter('append', lambda v, attr: '{0}{1}'.format(v, attr))

  cmds = []

  for tmpl, f in TEMPLATES.items():
    with open(os.path.join(args.templates, tmpl), 'r') as tf:
      engine = template.Engine()
      engine.template_builtins.append(register)
      body = engine.from_string(tf.read()).render(ctx)
      output_base = engine.from_string(f).render(ctx)
      output = os.path.join(tmp, output_base)
      if args.print:
          print('{0}:\n{1}\n'.format(output, body))
      elif args.diff:
        if not os.path.isfile(output):
          logging.info('Output file does not exist: %s', output)
        else:
          with open(output, 'r') as of:
            print('\n'.join(difflib.unified_diff(
              of.read().split('\n'),
              body.split('\n'),
              fromfile=output,
              tofile=tmpl)))
      else:
        os.makedirs(os.path.dirname(output), exist_ok=True)
        with open(output, 'w') as of:
          #logging.info('Writing %s..', output)
          diff = 'diff {0} {1}'.format(
              os.path.join(args.root, output_base),
              output)
          install = 'sudo install -v -m 644 -o root -g root -t {0} {1}'.format(
              os.path.join(args.root, os.path.dirname(output_base)),
              output)
          logging.info(diff)
          logging.info(install)
          cmds.append(install)
          of.write(body)

  logging.info('Install cmds:\n' + ' \\\n  && '.join(cmds))

  return os.EX_OK


if __name__ == '__main__':
  a = define_flags()
  logging.basicConfig(
      level=a.verbosity,
      datefmt='%Y/%m/%d %H:%M:%S',
      format='[%(asctime)s] %(levelname)s: %(message)s')
  sys.exit(main(a))

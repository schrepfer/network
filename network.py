#!/usr/bin/env python3

"""Generate network configurations."""

import config

import argparse
import difflib
import ipaddress
import logging
import os
import pathlib
import pprint
import re
import sys
import time
import yaml

from django import template                         # type: ignore
from django.template.loader import render_to_string # type: ignore
from django.conf import settings                    # type: ignore

from typing import Any, Optional, Union


TEMPLATES = {
  'etc/bind/db.0.0.0.0.tmpl': 'etc/bind/db.{{ network.network }}',
  'etc/bind/db.domain.tmpl': 'etc/bind/db.{{ domain }}',
  'etc/bind/named.conf.local.tmpl': 'etc/bind/named.conf.local',
  'etc/dhcp/dhcpd.conf.tmpl': 'etc/dhcp/dhcpd.conf',
  'etc/dnsmasq.conf.tmpl': 'etc/dnsmasq.conf',
  'etc/hosts.tmpl': 'etc/hosts',
  'etc/mailname.tmpl': 'etc/mailname',
  'etc/postfix/main.cf.tmpl': 'etc/postfix/main.cf',
  'etc/resolv.conf.tmpl': 'etc/resolv.conf',
  'tmp/edgerouter.txt.tmpl': 'tmp/edgerouter.txt',
  'var/www/html/index.html.tmpl': 'var/www/html/index.html',
  'var/www/html/style.css.tmpl': 'var/www/html/style.css',
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
      '--time', '-s',
      type=int,
      default=int(time.time()),
      help='the time to used in the output',
      metavar='SECONDS')
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
  """IPv4Address with custom reverse_pointer."""

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
  """IPv4Network with robust IP resolution."""

  def resolve(self, ip_str: str) -> IPv4Address:
    if ip_str.startswith('0.'):
      offset = int(ipaddress.IPv4Address(ip_str))
      addr = super().__getitem__(offset)
      return IPv4Address(int(addr), prefixlen=self.prefixlen)
    else:
      return IPv4Address(ip_str, prefixlen=self.prefixlen)

  def __getitem__(self, n: Union[int, str, ipaddress.IPv4Address]) -> IPv4Address:
    if isinstance(n, ipaddress.IPv4Address):
      if isinstance(n, IPv4Address):
        return n
      return IPv4Address(int(n), prefixlen=self.prefixlen)
    if isinstance(n, str):
      return self.resolve(n)
    addr = super().__getitem__(n)
    return IPv4Address(int(addr), prefixlen=self.prefixlen)

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

  @property
  def octets(self) -> tuple[int, ...]:
    return tuple((int(self.network_address) & 0xff << (i*8)) >> i*8 for i in [3, 2, 1, 0])


class Network(IPv4Network):
  """A network configuration with fallback support."""

  def __init__(self, cfg: dict[str, Any], parent: Optional['Network'] = None):
    super().__init__(cfg['network'])
    self.cfg = cfg
    self.parent = parent

  def __getattr__(self, name: str) -> Any:
    try:
      return self.cfg[name]
    except KeyError:
      if self.parent:
        try:
          return getattr(self.parent, name)
        except AttributeError:
          pass
      raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

  def get(self, name: str, default: Any = None) -> Any:
    try:
      return getattr(self, name)
    except AttributeError:
      return default

  # Properties with fallback support (raise AttributeError on missing key)

  @property
  def gateway(self) -> IPv4Address:
    try:
      return self[self.cfg['gateway']]
    except KeyError:
      raise AttributeError("gateway")

  @property
  def tags(self) -> list[str]:
    return self.cfg.get('tags', [])

  @property
  def dynamic_start(self) -> IPv4Address:
    try:
      return self[self.cfg['dynamic']['start']]
    except KeyError:
      raise AttributeError("dynamic_start")

  @property
  def dynamic_end(self) -> IPv4Address:
    try:
      return self[self.cfg['dynamic']['end']]
    except KeyError:
      raise AttributeError("dynamic_end")

  @property
  def dynamic_range(self) -> list[IPv4Address]:
    return [
        IPv4Address(ip, prefixlen=self.prefixlen)
        for ip in range(int(self.dynamic_start), int(self.dynamic_end) + 1)
    ]

  @property
  def safe_dns(self) -> IPv4Address:
    try:
      return self[self.cfg['safe_dns']]
    except KeyError:
      raise AttributeError("safe_dns")

  @property
  def known_dns(self) -> IPv4Address:
    try:
      return self[self.cfg['known_dns']]
    except KeyError:
      raise AttributeError("known_dns")

  @property
  def unifi(self) -> IPv4Address:
    try:
      return self[self.cfg['unifi']]
    except KeyError:
      raise AttributeError("unifi")

  @property
  def ns(self) -> IPv4Address:
    try:
      return self[self.cfg['ns']]
    except KeyError:
      raise AttributeError("ns")

  @property
  def mail(self) -> IPv4Address:
    try:
      return self[self.cfg['mail']]
    except KeyError:
      raise AttributeError("mail")

  @property
  def dns_servers(self) -> list[IPv4Address]:
    try:
      return [self[ip] for ip in self.cfg['dns_servers']]
    except KeyError:
      raise AttributeError("dns_servers")

  @property
  def ntp(self) -> list[IPv4Address]:
    try:
      return [self[ip] for ip in self.cfg['ntp']]
    except KeyError:
      raise AttributeError("ntp")


def check_flags(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
  # See: http://docs.python.org/2/library/argparse.html#exiting-methods
  return None


def main(args: argparse.Namespace) -> int:
  if not args.config:
    return 1

  if not args.templates:
    return 1

  if not args.root:
    return 1

  tmp = '/tmp/network-%d' % os.getuid()
  cfg = config.load_yaml(args.config)
  cfg['time'] = args.time

  pp = pprint.PrettyPrinter(indent=1)
  logging.debug('Config: %s', pp.pformat(cfg))

  network = Network(cfg)
  vlans = [Network(vlan, parent=network) for vlan in cfg.get('vlans', [])]

  # Pre-resolve config IPs relative to core network
  cfg['gateway'] = network.gateway
  if 'ns' in cfg:
    cfg['ns'] = network.ns
  if 'mail' in cfg:
    cfg['mail'] = network.mail
  if 'known_dns' in cfg:
    cfg['known_dns'] = network.known_dns
  if 'safe_dns' in cfg:
    cfg['safe_dns'] = network.safe_dns
  if 'unifi' in cfg:
    cfg['unifi'] = network.unifi
  if 'dns_servers' in cfg:
    cfg['dns_servers'] = network.dns_servers
  if 'ntp' in cfg:
    cfg['ntp'] = network.ntp
  if 'dynamic' in cfg:
    cfg['dynamic']['start'] = network.dynamic_start
    cfg['dynamic']['end'] = network.dynamic_end

  for host in cfg['hosts']:
    if 'ip' in host:
      host['ip'] = network[host['ip']]

  # Sort it by the IPv4Address value
  cfg['hosts'] = sorted(cfg['hosts'], key=lambda x: x.get('ip'))

  # Pre-resolve and sort VLAN hosts
  for vlan in vlans:
    vlan_cfg = vlan.cfg
    if 'hosts' in vlan_cfg:
      for host in vlan_cfg['hosts']:
        if 'ip' in host:
          host['ip'] = vlan[host['ip']]
      vlan_cfg['hosts'] = sorted(vlan_cfg['hosts'], key=lambda x: x.get('ip'))

  cfg.update({
    'home': pathlib.Path.home(),
    'network': network,
    'vlans': vlans,
  })

  settings.configure(DEBUG=True)
  ctx = template.Context(cfg)
  register = template.Library()

  register.filter('format', lambda v, fmt: v.format(fmt))

  cmds = []
  mkdirs = set()
  num_diffs = 0

  for tmpl, f in TEMPLATES.items():
    with open(os.path.join(args.templates, tmpl), 'r') as tf:
      engine = template.Engine()
      engine.template_builtins.append(register)
      body = engine.from_string(tf.read()).render(ctx)
      output_base = engine.from_string(f).render(ctx)
      output = os.path.join(tmp, output_base)
      final_output = os.path.join(args.root, output_base)
      if args.print:
        print('{0}:\n{1}\n'.format(output, body))
      elif args.diff:
        if not os.path.isfile(final_output):
          logging.info('Output file does not exist: %s', final_output)
        else:
          with open(final_output, 'r') as of:
            if diffs := list(difflib.unified_diff(
                of.read().split('\n'),
                body.split('\n'),
                fromfile=final_output,
                tofile=tmpl)):
              print('\n'.join(diffs))
              num_diffs += 1
      else:
        os.makedirs(os.path.dirname(output), exist_ok=True)
        with open(output, 'w') as of:
          output_dir = os.path.join(args.root, os.path.dirname(output_base))
          if output_dir not in mkdirs:
            mkdir = f'sudo mkdir -p {output_dir}'
            cmds.append(mkdir)
            mkdirs.add(output_dir)
          install = f'sudo install -v -m 644 -o root -g root -t {output_dir} {output}'
          cmds.append(install)
          of.write(body)

  if cmds:
    logging.info('Install cmds:\n' + ' \\\n  && '.join(cmds))

  return num_diffs


if __name__ == '__main__':
  a = define_flags()
  logging.basicConfig(
      level=a.verbosity,
      datefmt='%Y/%m/%d %H:%M:%S',
      format='[%(asctime)s] %(levelname)s: %(message)s')
  sys.exit(main(a))

import logging
import yaml
from typing import Any, Optional

import schema # type: ignore


class IPAddress:
  def validate(self, data, **kwargs):
    return schema.And(
      str,
      schema.Regex(r'^\d+([.]\d+){3}$', error='Must match an IP/MASK'),
      lambda s: all(0 <= int(n) <= 255 for n in s.split('.', 3)),
      error='Invalid IP address',
    ).validate(data, **kwargs)


class Network:
  def validate(self, data, **kwargs):
    ret = schema.Regex(
        r'^\d+([.]\d+){3}/\d+$', error='Must match an IP/MASK'
    ).validate(data, **kwargs)
    parts = ret.split('/')
    IPAddress().validate(parts[0], **kwargs)
    schema.Schema(lambda n: 0 <= int(n) <= 32, error='Network MASK must be between 0 and 32').validate(parts[1])
    return ret


class HardwareAddress:
  def validate(self, data, **kwargs):
    return schema.And(
      str,
      schema.Use(lambda s: str.lower(s).replace('-', ':')),
      schema.Regex(r'^[0-9a-f]{2}(:[0-9a-f]{2}){5}$'),
    ).validate(data, **kwargs)


class Format:
  def __init__(self, test_value):
    self._test_value = test_value

  def validate(self, data, **kwargs):
    data = schema.Schema(str).validate(data, **kwargs)
    try:
      data.format(self._test_value)
    except Exception as e:
      raise schema.SchemaError(None, str(e))
    return data
  

SCHEMA = schema.Schema(
  {
    'domain': str,
    'gateway': IPAddress(),
    'network': Network(),
    'ntp': [IPAddress()],
    'dns': [IPAddress()],
    'ns': IPAddress(),
    'mail': IPAddress(),
    'dynamic': {
      'start': IPAddress(),
      'end': IPAddress(),
      'format': Format(0),
    },
    'hosts': [
      {
        schema.Optional('hardware'): HardwareAddress(),
        'ip': IPAddress(),
        'hostname': str,
        schema.Optional('aliases'): [str],
        schema.Optional('description'): str
      }
    ]
  },
)


class ConfigError(Exception):
  """Config wrapped errors."""


def validate(cfg: Any) -> Any:
  hostnames = set()
  hardwares = set()
  ips = set()
  errors = []

  for i, host in enumerate(cfg['hosts']):
    if hostname := host.get('hostname'):
      if hostname in hostnames:
        errors.append(f'hosts[{i:d}].hostname {hostname!r} already used')
      else:
        hostnames.add(hostname)
    if aliases := host.get('aliases'):
      for j, alias in enumerate(host['aliases']):
        if alias in hostnames:
          errors.append(f'hosts[{i:d}].aliases[{j:d}] {alias!r} already used')
        else:
          hostnames.add(alias)
    else:
      host['aliases'] = []
    if hardware := host.get('hardware'):
      if hardware in hardwares:
        errors.append(f'hosts[{i:d}].hardware {hardware!r} already used')
      else:
        hardwares.add(hardware)
    else:
      host['hardware'] = None
    if ip := host.get('ip'):
      if ip in ips:
        errors.append(f'hosts[{i:d}].ip {ip!r} already used')
      else:
        ips.add(ip)
    if 'description' not in host:
      host['description'] = None

  if errors:
    raise ConfigError('Errors:\n\t' + ('\n\t'.join(errors)))

  return cfg


def load_yaml(f: str) -> Any:
  with open(f) as fh:
    cfg = yaml.load(fh, Loader=yaml.Loader)

  try:
    cfg = SCHEMA.validate(cfg)

  except schema.SchemaError as e:
    raise ConfigError(e)

  return validate(cfg)


def normalize(mac: str) -> str:
  return mac.lower().replace('-', ':')

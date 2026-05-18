#!/usr/bin/env python3

import unittest
import ipaddress
import schema
import sys
import os

# Add local deps to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'deps'))

import config
import network

class ConfigValidationTest(unittest.TestCase):

  def test_valid_config(self):
    cfg = {
      'domain': 'test.domain',
      'name': 'LAN',
      'gateway': '0.0.0.1',
      'network': '10.10.0.0/16',
      'ntp': ['0.0.0.50'],
      'unifi': '0.0.0.50',
      'safe_dns': '0.0.0.49',
      'known_dns': '0.0.0.50',
      'dns_servers': ['0.0.0.1'],
      'ns': '0.0.0.50',
      'mail': '0.0.0.50',
      'dynamic': {
        'start': '0.0.100.0',
        'end': '0.0.101.255',
        'format': 'host-{}',
      },
      'vlans': [
        {
          'name': 'VLAN30',
          'gateway': '10.30.0.1',
          'network': '10.30.0.0/16',
          'dynamic': {
            'start': '0.0.100.0',
            'end': '0.0.100.255',
            'format': 'vlan30-{}',
          },
          'hosts': [
            {
              'hardware': '00:11:22:33:44:55',
              'ip': '0.0.0.99',
              'hostname': 'vlan30-host',
            }
          ]
        }
      ],
      'hosts': [
        {
          'hardware': 'aa:bb:cc:dd:ee:ff',
          'ip': '0.0.0.50',
          'hostname': 'core-host',
        }
      ]
    }
    # Should validate without error
    validated = config.SCHEMA.validate(cfg)
    self.assertEqual(config.validate(validated), validated)

  def test_duplicate_global_hostname(self):
    cfg = {
      'domain': 'test.domain',
      'name': 'LAN',
      'gateway': '0.0.0.1',
      'network': '10.10.0.0/16',
      'ntp': ['0.0.0.50'],
      'unifi': '0.0.0.50',
      'safe_dns': '0.0.0.49',
      'known_dns': '0.0.0.50',
      'dns_servers': ['0.0.0.1'],
      'ns': '0.0.0.50',
      'mail': '0.0.0.50',
      'dynamic': {
        'start': '0.0.100.0',
        'end': '0.0.101.255',
        'format': 'host-{}',
      },
      'vlans': [
        {
          'name': 'VLAN30',
          'gateway': '10.30.0.1',
          'network': '10.30.0.0/16',
          'dynamic': {
            'start': '0.0.100.0',
            'end': '0.0.100.255',
            'format': 'vlan30-{}',
          },
          'hosts': [
            {
              'hardware': '00:11:22:33:44:55',
              'ip': '0.0.0.99',
              'hostname': 'duplicate-name', # Duplicate!
            }
          ]
        }
      ],
      'hosts': [
        {
          'hardware': 'aa:bb:cc:dd:ee:ff',
          'ip': '0.0.0.50',
          'hostname': 'duplicate-name', # Duplicate!
        }
      ]
    }
    validated = config.SCHEMA.validate(cfg)
    with self.assertRaises(config.ConfigError) as ctx:
      config.validate(validated)
    self.assertIn("already used", str(ctx.exception))

  def test_duplicate_global_hardware(self):
    cfg = {
      'domain': 'test.domain',
      'name': 'LAN',
      'gateway': '0.0.0.1',
      'network': '10.10.0.0/16',
      'ntp': ['0.0.0.50'],
      'unifi': '0.0.0.50',
      'safe_dns': '0.0.0.49',
      'known_dns': '0.0.0.50',
      'dns_servers': ['0.0.0.1'],
      'ns': '0.0.0.50',
      'mail': '0.0.0.50',
      'dynamic': {
        'start': '0.0.100.0',
        'end': '0.0.101.255',
        'format': 'host-{}',
      },
      'vlans': [
        {
          'name': 'VLAN30',
          'gateway': '10.30.0.1',
          'network': '10.30.0.0/16',
          'dynamic': {
            'start': '0.0.100.0',
            'end': '0.0.100.255',
            'format': 'vlan30-{}',
          },
          'hosts': [
            {
              'hardware': 'aa:bb:cc:dd:ee:ff', # Duplicate!
              'ip': '0.0.0.99',
              'hostname': 'vlan-host',
            }
          ]
        }
      ],
      'hosts': [
        {
          'hardware': 'aa:bb:cc:dd:ee:ff', # Duplicate!
          'ip': '0.0.0.50',
          'hostname': 'core-host',
        }
      ]
    }
    validated = config.SCHEMA.validate(cfg)
    with self.assertRaises(config.ConfigError) as ctx:
      config.validate(validated)
    self.assertIn("already used", str(ctx.exception))

  def test_duplicate_local_ip_same_segment(self):
    cfg = {
      'domain': 'test.domain',
      'name': 'LAN',
      'gateway': '0.0.0.1',
      'network': '10.10.0.0/16',
      'ntp': ['0.0.0.50'],
      'unifi': '0.0.0.50',
      'safe_dns': '0.0.0.49',
      'known_dns': '0.0.0.50',
      'dns_servers': ['0.0.0.1'],
      'ns': '0.0.0.50',
      'mail': '0.0.0.50',
      'dynamic': {
        'start': '0.0.100.0',
        'end': '0.0.101.255',
        'format': 'host-{}',
      },
      'vlans': [],
      'hosts': [
        {
          'hardware': 'aa:bb:cc:dd:ee:11',
          'ip': '0.0.0.50', # Duplicate IP!
          'hostname': 'host1',
        },
        {
          'hardware': 'aa:bb:cc:dd:ee:22',
          'ip': '0.0.0.50', # Duplicate IP!
          'hostname': 'host2',
        }
      ]
    }
    validated = config.SCHEMA.validate(cfg)
    with self.assertRaises(config.ConfigError) as ctx:
      config.validate(validated)
    self.assertIn("already used in this network segment", str(ctx.exception))

  def test_allow_duplicate_relative_ip_different_segments(self):
    cfg = {
      'domain': 'test.domain',
      'name': 'LAN',
      'gateway': '0.0.0.1',
      'network': '10.10.0.0/16',
      'ntp': ['0.0.0.50'],
      'unifi': '0.0.0.50',
      'safe_dns': '0.0.0.49',
      'known_dns': '0.0.0.50',
      'dns_servers': ['0.0.0.1'],
      'ns': '0.0.0.50',
      'mail': '0.0.0.50',
      'dynamic': {
        'start': '0.0.100.0',
        'end': '0.0.101.255',
        'format': 'host-{}',
      },
      'vlans': [
        {
          'name': 'VLAN30',
          'gateway': '10.30.0.1',
          'network': '10.30.0.0/16',
          'dynamic': {
            'start': '0.0.100.0',
            'end': '0.0.100.255',
            'format': 'vlan30-{}',
          },
          'hosts': [
            {
              'hardware': '00:11:22:33:44:55',
              'ip': '0.0.0.50', # Same relative IP but in VLAN30!
              'hostname': 'vlan30-host',
            }
          ]
        }
      ],
      'hosts': [
        {
          'hardware': 'aa:bb:cc:dd:ee:ff',
          'ip': '0.0.0.50', # Same relative IP in core!
          'hostname': 'core-host',
        }
      ]
    }
    # Should pass validation because they are in different segments
    validated = config.SCHEMA.validate(cfg)
    self.assertEqual(config.validate(validated), validated)

  def test_invalid_vlan_name(self):
    cfg = {
      'name': 'LAN30 with spaces', # Invalid!
    }
    with self.assertRaises(schema.SchemaError):
      config.Name().validate(cfg['name'])

  def test_invalid_hostname(self):
    invalid_names = ['UPPERCASE', 'host_with_underscore', 'host.', '-host', '']
    for name in invalid_names:
      with self.subTest(name=name):
        with self.assertRaises(schema.SchemaError):
          config.Hostname().validate(name)

class NetworkModelTest(unittest.TestCase):

  def setUp(self):
    self.cfg = {
      'domain': 'test.domain',
      'name': 'LAN',
      'gateway': '0.0.0.1',
      'network': '10.10.0.0/16',
      'ntp': ['0.0.0.50'],
      'unifi': '0.0.0.50',
      'safe_dns': '0.0.0.49',
      'known_dns': '0.0.0.50',
      'dns_servers': ['0.0.0.1'],
      'ns': '0.0.0.50',
      'mail': '0.0.0.50',
      'dynamic': {
        'start': '0.0.100.0',
        'end': '0.0.101.255',
        'format': 'host-{}',
      },
      'vlans': [
        {
          'name': 'VLAN30',
          'gateway': '10.30.0.1',
          'network': '10.30.0.0/16',
          'dynamic': {
            'start': '0.0.100.0',
            'end': '0.0.100.255',
            'format': 'vlan30-{}',
          },
          'hosts': [
            {
              'hardware': '00:11:22:33:44:55',
              'ip': '0.0.0.99',
              'hostname': 'vlan30-host',
            }
          ]
        }
      ],
      'hosts': [
        {
          'hardware': 'aa:bb:cc:dd:ee:ff',
          'ip': '0.0.0.50',
          'hostname': 'core-host',
        }
      ]
    }
    self.core_net = network.Network(self.cfg)
    self.vlan_net = network.Network(self.cfg['vlans'][0], parent=self.core_net)

  def test_ip_resolution(self):
    # Core relative IP
    self.assertEqual(str(self.core_net['0.0.0.50']), '10.10.0.50')
    # VLAN relative IP (VLAN subnet is 10.30.0.0/16)
    self.assertEqual(str(self.vlan_net['0.0.0.99']), '10.30.0.99')
    # Absolute IP
    self.assertEqual(str(self.vlan_net['8.8.8.8']), '8.8.8.8')

  def test_parent_fallback(self):
    # VLAN doesn't define domain, should fallback to core
    self.assertEqual(self.vlan_net.domain, 'test.domain')
    # VLAN doesn't define safe_dns, should fallback to core's resolved safe_dns
    self.assertEqual(str(self.vlan_net.safe_dns), '10.10.0.49')

  def test_properties(self):
    self.assertEqual(str(self.core_net.gateway), '10.10.0.1')
    self.assertEqual(str(self.vlan_net.gateway), '10.30.0.1')
    self.assertEqual(str(self.vlan_net.dynamic_start), '10.30.100.0')

if __name__ == '__main__':
  unittest.main()

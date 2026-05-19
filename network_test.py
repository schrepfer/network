#!/usr/bin/env python3

import unittest
import ipaddress
import schema
import sys
import os
import argparse
from django import template

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

class ContextPreparationTest(unittest.TestCase):

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
          'hosts': [
            {'hostname': 'vlan30-host-2', 'ip': '0.0.0.100'},
            {'hostname': 'vlan30-host-1', 'ip': '0.0.0.50'}
          ]
        }
      ],
      'hosts': [
        {'hostname': 'core-host-2', 'ip': '0.0.0.50'},
        {'hostname': 'core-host-1', 'ip': '0.0.0.10'}
      ]
    }
    self.args = argparse.Namespace(time=12345)

  def test_prepare_context_sorting(self):
    ctx = network.prepare_context(self.cfg, self.args)

    # Verify global hosts are sorted by IP
    self.assertEqual(ctx['hosts'][0]['hostname'], 'core-host-1')
    self.assertEqual(ctx['hosts'][1]['hostname'], 'core-host-2')

    # Verify VLAN hosts are sorted by IP
    vlan30 = ctx['vlans'][0]
    self.assertEqual(vlan30.cfg['hosts'][0]['hostname'], 'vlan30-host-1')
    self.assertEqual(vlan30.cfg['hosts'][1]['hostname'], 'vlan30-host-2')

  def test_prepare_context_resolution(self):
    ctx = network.prepare_context(self.cfg, self.args)

    # Verify IP resolution
    self.assertEqual(str(ctx['hosts'][0]['ip']), '10.10.0.10')
    self.assertEqual(str(ctx['gateway']), '10.10.0.1')

    vlan30 = ctx['vlans'][0]
    self.assertEqual(str(vlan30.cfg['hosts'][0]['ip']), '10.30.0.50')
    self.assertEqual(str(vlan30.gateway), '10.30.0.1')


class TemplateRenderingTest(unittest.TestCase):

  def setUp(self):
    self.register = template.Library()
    self.register.filter('format', lambda v, fmt: v.format(fmt))

    # Minimal context
    self.context = {
      'domain': 'test.domain',
      'name': 'LAN',
      'hosts': [
        {'hostname': 'host1', 'ip': '10.10.0.10', 'hardware': '11:22:33:44:55:66', 'description': 'Desc 1', 'aliases': ['alias1']}
      ],
      'vlans': [
        {
          'name': 'VLAN30',
          'description': 'IoT',
          'cfg': {
            'hosts': [
              {'hostname': 'vlan-host1', 'ip': '10.30.0.10', 'hardware': 'aa:bb:cc:dd:ee:ff', 'description': 'VLAN Desc 1'}
            ]
          }
        },
        {
          'name': 'VLAN40',
          'description': 'Empty VLAN',
          'cfg': {} # No hosts
        }
      ]
    }

  def test_index_html_rendering(self):
    # We can read the actual template file
    tmpl_path = os.path.join(os.path.dirname(__file__), 'templates/var/www/html/index.html.tmpl')
    with open(tmpl_path, 'r') as f:
      tmpl_content = f.read()

    rendered = network.render_template(tmpl_content, self.context, self.register)

    # Assertions
    self.assertIn('<h2>LAN</h2>', rendered)
    self.assertIn('host1', rendered)
    self.assertIn('10.10.0.10', rendered)
    self.assertIn('11:22:33:44:55:66', rendered)
    self.assertIn('Desc 1', rendered)
    self.assertIn('alias1', rendered)

    # VLAN30 has hosts, should have header and table
    self.assertIn('<h2>VLAN30 - IoT</h2>', rendered)
    self.assertIn('vlan-host1', rendered)
    self.assertIn('10.30.0.10', rendered)

    # VLAN40 has no hosts, should NOT have header or table
    self.assertNotIn('VLAN40', rendered)
    self.assertNotIn('Empty VLAN', rendered)

  def test_index_html_hidden_hosts(self):
    tmpl_path = os.path.join(os.path.dirname(__file__), 'templates/var/www/html/index.html.tmpl')
    with open(tmpl_path, 'r') as f:
      tmpl_content = f.read()

    context = dict(self.context)
    context['hosts'] = [
      {'hostname': 'visible-host', 'ip': '10.10.0.10'},
      {'hostname': 'hidden-host', 'ip': '10.10.0.11', 'tags': ['hidden']}
    ]

    rendered = network.render_template(tmpl_content, context, self.register)

    self.assertIn('visible-host', rendered)
    self.assertNotIn('hidden-host', rendered)

if __name__ == '__main__':
  unittest.main()

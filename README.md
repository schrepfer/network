# Network

## Install

You need django templates available to use this. You can install this via **apt** or **pip3
install**.

```shell
apt install python3-django
```

## Configuration

Save your configuration file as `DOMAIN.yml` where that may be `x.wabb.it.yml`.

```yaml
domain: 'x.wabb.it'
gateway: '10.20.0.1'
network: '10.20.0.0/16'
ntp:
  - 0.0.0.50
dns:
  - 10.20.0.50
  - 10.20.0.1
ns: 0.0.0.50
mail: 0.0.0.50
dynamic:
  start: '0.0.100.0'
  end: '0.0.101.255'
  format: 'goomba-{}'
hosts:
  -
    hardware: '01:02:03:04:05:01'
    ip: '0.0.0.50'
    hostname: 'wario'
    aliases:
      - 'ntp'
      - 'time'
      - 'pihole'
      - 'smtp'
      - 'unifi'
      - 'www'
      - 'smtp'
      - 'mail'
    description: 'SuperMicro server mounted in the rack.'
  -
    hardware: '01:02:03:04:05:02'
    ip: '0.0.0.90'
    hostname: 'old-blooper'
  -
    hardware: '01:02:03:04:05:03'
    ip: '0.0.0.95'
    hostname: 'blooper'
    aliases:
      - 'printer'
      - 'brother'
    description: "This is the HP Printer in my office."
  -
    hardware: '01:02:03:04:05:04'
    ip: '0.0.0.1'
    hostname: 'chain-chomp'
    aliases:
      - 'router'
      - 'gateway'
  -
    hardware: '01:02:03:04:05:05'
    ip: '0.0.0.2'
    hostname: 'bullet-bill'
  -
    hardware: '01:02:03:04:05:06'
    ip: '0.0.0.5'
    hostname: 'petey-piranha'
    aliases:
      - 'es48-500w'
      - 'switch'
    description: 'Ubiquiti ES-48-500W network Switch.'
  -
    hardware: '01:02:03:04:05:07'
    ip: '0.0.0.10'
    hostname: 'nanohd-lower'
    aliases:
      - 'ap-lower'
    description: 'Unifi AP on Lower level (Hallway).'
  -
    hardware: '01:02:03:04:05:08'
    ip: '0.0.0.11'
    hostname: 'nanohd-main'
    aliases:
      - 'ap-main'
    description: 'Unifi AP on Main level (Great room).'
  -
    hardware: '01:02:03:04:05:09'
    ip: '0.0.0.12'
    hostname: 'nanohd-upper'
    aliases:
      - 'ap-upper'
    description: 'Unifi AP on Upper level (Hallway).'
  -
    hardware: '01:02:03:04:05:0a'
    ip: '0.0.0.13'
    hostname: 'acpro-deck'
    aliases:
      - 'ap-deck'
    description: 'Unifi AP on Main level (Deck).'
  -
    hardware: '01:02:03:04:05:0b'
    ip: '0.0.0.20'
    hostname: 'boo'
    description: 'Raspberry Pi that watches network traffic.'
  -
    hardware: '01:02:03:04:05:0c'
    ip: '0.0.0.55'
    hostname: 'wiggler'
    description: 'Network storage server running TrueNAS.'
  -
    hardware: '01:02:03:04:05:0d'
    ip: '0.0.0.56'
    hostname: 'wiggler-plex'
  -
    hardware: '01:02:03:04:05:0e'
    ip: '0.0.0.45'
    hostname: 'waluigi'
    aliases:
      - 'alex'
    description: "Alex's windows desktop."
  -
    hardware: '01:02:03:04:05:0f'
    ip: '0.0.0.46'
    hostname: 'waluigi-wifi'
  -
    hardware: '01:02:03:04:05:10'
    ip: '0.0.0.40'
    hostname: 'toadette'
    aliases:
      - 'tina'
    description: "Tina's windows desktop."
  -
    hardware: '01:02:03:04:05:11'
    ip: '0.0.0.41'
    hostname: 'toadette-wifi'
  -
    hardware: '01:02:03:04:05:12'
    ip: '0.0.10.1'
    hostname: 'camera-0'
```

## Execution

```
usage: network.py [-h] [-v LEVEL] [--root DIR] [--print] [--diff]
                  [--templates DIR] [--config PATH] [-V]

Generate network configurations.

optional arguments:
  -h, --help            show this help message and exit
  -v LEVEL, --verbosity LEVEL
                        the logging verbosity
  --root DIR, -r DIR    the output root; where the files end up
  --print, -p           print the configuration only
  --diff, -d            diff the output only
  --templates DIR, -t DIR
                        path where the templates live
  --config PATH, -f PATH
                        path to the config file
  -V, --version         show program's version number and exit
```

### Example

```shell
./network.py -f x.wabb.it.yml -d
```

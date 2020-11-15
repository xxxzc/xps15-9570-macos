import argparse
import json
import platform
import plistlib
import re
from base64 import b64decode, b64encode
from copy import deepcopy
from datetime import date, datetime
from os import system as _sh
from pathlib import Path
from subprocess import check_output
from urllib.request import Request, urlopen, urlretrieve
from shutil import rmtree
from typing import List

ISWIN = platform.system() == 'Windows'
DEFAULT_CLOVER_THEME = 'Nightwish'

KEXT_PLUGINS_TO_DELETE = {
    'VoodooPS2Controller.kext': ('VoodooPS2Mouse.kext', 'VoodooPS2Trackpad.kext', 'VoodooInput.kext'),
    'AirportBrcmFixup.kext': ('AirPortBrcm4360_Injector.kext',)
}
ORDERED_KEXTS = ['Lilu.kext', 'VirtualSMC.kext',
                 'CPUFriend.kext', 'CPUFriendDataProvider.kext',
                 'AppleALC.kext', 'VoodooInput.kext',
                 'VoodooGPIO.kext', 'VoodooI2CServices.kext',
                 'VoodooI2C.kext', 'VoodooI2CHID.kext']
DEFAULT_PRIORITY = len(ORDERED_KEXTS)
KEXTS_PRIORITY = dict(zip(ORDERED_KEXTS, range(DEFAULT_PRIORITY)))


class Urls:
    CLOVER_THEME_URL = 'git://git.code.sf.net/p/cloverefiboot/themes'
    IASL_DOWNLOAD_URL = 'https://bitbucket.org/RehabMan/acpica/downloads/iasl.zip'
    MACSERIAL = 'https://raw.githubusercontent.com/daliansky/Hackintosh/master/Tools/macserial'
    ONE_KEY_CPUFRIEND = 'https://raw.githubusercontent.com/stevezhengshiqi/one-key-cpufriend/master/one-key-cpufriend.sh'
    GITHUB_TOKEN = 'NWFhNjIyNzc0ZDM2NzU5NjM3NTE2ZDg3MzdhOTUyOThkNThmOTQ2Mw=='


ROOT = Path(__file__).absolute().parent
TMP = ROOT / 'tmp'
ACPI = ROOT / 'ACPI'
PACKAGES_CSV = ROOT / 'packages.csv'


def sh(*args):
    if ISWIN:
        return
    _sh(' '.join(map(str, args)))


def shout(cmd) -> str:
    '''sh cmd then return output
    '''
    return check_output(cmd, shell=True, encoding='utf-8').strip()


def name_without_ext(p: Path) -> str:
    return p.name.split('.')[0]


def download(url, path, executable=True):
    path.parent.mkdir(exist_ok=True, parents=True)
    sh(f'curl -fsSL {url} -o {path}')
    if executable:
        sh('chmod +x', path)


'''
TERMINAL
'''


class Terminal:
    _ERROR = 'x'
    _TITLE = '::'
    _ACTION = '==>'
    _SUCCESS = '√'

    @staticmethod
    def error(*msg):
        print(Terminal._ERROR, *msg)
        exit(1)

    @staticmethod
    def title(*msg):
        print(Terminal._TITLE, *msg)

    @staticmethod
    def success(*msg):
        print(Terminal._SUCCESS, *msg)

    @staticmethod
    def prompt(msg: str) -> str:
        return input(f"{Terminal._ACTION} {msg}")

    @staticmethod
    def confirm(msg: str) -> bool:
        return Terminal.prompt(msg + '?(Y/n)') != 'n'


'''
CONFIG
'''


class Plist:
    SPLITTER = '>'

    def __init__(self, filepath: Path, keymap: {}):
        self.file = filepath
        self.keymap = keymap
        self.value = {}
        if filepath.exists():
            with open(self.file, 'rb') as f:
                self.value = plistlib.load(f)

    def save(self):
        with open(self.file, 'wb') as f:
            plistlib.dump(self.value, f)

    @staticmethod
    def data(s: str) -> bytes:
        if s.isdigit():  # '1'
            return bytes(map(int, s))
        elif s.startswith('0x'):  # '0x191b0000'
            return bytes.fromhex(''.join(s[i:i+2] for i in range(len(s)-2, 0, -2)))
        return b64decode(s)  # 'Ag==' -> b'\x02'

    def real_key(self, key: str) -> list:
        return self.keymap.get(key, key).split(self.SPLITTER)

    def index(self, key: str) -> tuple:
        '''return real key and the plist that contains this key
        '''
        keys = self.real_key(key)
        parent = self.value
        try:
            for k in keys[:-1]:
                parent = parent[k]
        except KeyError:
            Terminal.error(key, 'not found')
        return (keys[-1], parent)

    def get(self, key):
        '''return parent[key]
        '''
        key, parent = self.index(key)
        return parent[key]

    def set(self, key, value):
        '''set plist[key] to value, return old value and new value
        '''
        key, parent = self.index(key)

        if key not in parent:
            oldvalue = Plist.data('')
        else:
            oldvalue = parent[key]

        if key not in parent or type(oldvalue) is bytes and type(value) is not bytes:
            value = Plist.data(value)
        else:
            value = type(oldvalue)(value)

        parent[key] = value
        return oldvalue, value

    def delete(self, key):
        key, parent = self.index(key)
        parent.pop(key, 0)


class Bootloader:
    def __init__(self, path: Path, foldermap: dict, keymap: dict):
        self.path = path
        self.config = Plist(path / 'config.plist', keymap)
        self.foldermap = foldermap
        self.keymap = keymap
        self.name = path.name.lower()
        self.exist = self.path.exists()
        self.ACPI = self.real_path('ACPI')
        self.Drivers = self.real_path('Drivers')
        self.Kexts = self.real_path('Kexts')
        self.Tools = self.real_path('Tools')
        self.Themes = self.real_path('Themes')

    def real_path(self, foldername: str) -> Path:
        return self.path / self.foldermap.get(foldername, foldername)


CLOVER = Bootloader(ROOT / 'CLOVER', foldermap=dict(
    ACPI='ACPI/patched',
    Kexts='kexts/Other',
    Drivers='drivers/UEFI',
    Tools='tools',
    Theme='themes'
), keymap=dict(
    sn='SMBIOS>SerialNumber',
    mlb='SMBIOS>BoardSerialNumber',
    smuuid='SMBIOS>SmUUID',
    uiscale='BootGraphics>UIScale',
    theme='GUI>Theme',
    bootarg='Boot>Arguments',
    timeout='Boot>Timeout',
    defaultvolume='Boot>DefaultVolume',
    layoutid='Devices>Properties>PciRoot(0x0)/Pci(0x1f,0x3)>layout-id',
    dmlr='Devices>Properties>PciRoot(0x0)/Pci(0x2,0x0)>dpcd-max-link-rate',
    edid='Devices>Properties>PciRoot(0x0)/Pci(0x2,0x0)>AAPL00,override-no-connect',
    properties='Devices>Properties',
    booterquirks='Quirks',
    product='SMBIOS>ProductName'
))
OC = Bootloader(ROOT / 'OC', foldermap={}, keymap=dict(
    sn='PlatformInfo>Generic>SystemSerialNumber',
    mlb='PlatformInfo>Generic>MLB',
    smuuid='PlatformInfo>Generic>SystemUUID',
    uiscale='NVRAM>Add>4D1EDE05-38C7-4A6A-9CC6-4BCCA8B38C14>UIScale',
    bootarg='NVRAM>Add>7C436110-AB2A-4BBB-A880-FE41995C9F82>boot-args',
    timeout='Misc>Boot>Timeout',
    layoutid='DeviceProperties>Add>PciRoot(0x0)/Pci(0x1f,0x3)>layout-id',
    dmlr='DeviceProperties>Add>PciRoot(0x0)/Pci(0x2,0x0)>dpcd-max-link-rate',
    edid='DeviceProperties>Add>PciRoot(0x0)/Pci(0x2,0x0)>AAPL00,override-no-connect',
    properties='DeviceProperties>Add',
    booterquirks='Booter>Quirks',
    product='PlatformInfo>Generic>SystemProductName'
))

BOOTLOADERS: List[Bootloader] = [i for i in [OC, CLOVER] if i.exist]

PRODUCT = BOOTLOADERS[0].config.get('product')


def set_config(bootloader: Bootloader, kvs):
    '''update config with key=value pairs
    e.g.
    'uiscale=1' for FHD display
    'theme=Nightwish' to set Clover theme
    'bootarg--v bootarg+darkwake=1' to set bootargs
    '''
    if not bootloader.exist:
        return

    if type(kvs) is str:
        kvs = kvs.split(' ')

    config = bootloader.config

    Terminal.title('Setting', config.file)

    bootargs = []
    for kv in kvs:
        if kv.startswith('bootarg'):
            bootargs.append(kv)
            continue

        key, value = kv.split('=', 1)

        if key == 'theme':
            if bootloader.name == 'clover':
                download_theme(bootloader, value)
                bootloader.config.set('theme', value)
            continue

        old, new = config.set(key, value)
        Terminal.success('set', '>'.join(
            config.real_key(key)), 'from', old, 'to', new)

    if bootargs:
        arg, boot = config.index('bootarg')
        # { '-v': '-v', 'darkwake': 'darkwake=1'}
        argset = set(x for x in boot[arg].split(' ') if x)
        for bootarg in bootargs:
            if bootarg[7] == '-':  # delete
                argset.remove(bootarg[8:])
            else:
                argset.add(bootarg[8:])
        boot[arg] = ' '.join(argset)
        Terminal.success('Set bootargs to ', boot[arg])
    return


def set_configs(kvs):
    for bootloader in BOOTLOADERS:
        set_config(bootloader, kvs)


'''
THEME
'''


def download_theme(bootloader: Bootloader, theme: str):
    if not bootloader.exist:
        return

    if bootloader.name == 'clover':
        themefolder = bootloader.Themes
        themefolder.mkdir(exist_ok=True)
        theme = themefolder / theme
        if not theme.exists() or Terminal.confirm('Theme {} exists, do you want to update it'.format(theme.name)):
            Terminal.title('Downloading theme', theme.name)
            sh('cd {} && git archive --remote={} HEAD themes/{} | tar -x -v'.format(
               themefolder.parent, Urls.CLOVER_THEME_URL, theme.name))
            Terminal.success('Theme', theme.name,
                             'downloaded into', themefolder)
            print()
    return


def update_themes(bootloader):
    if not bootloader.exist:
        return

    themes = bootloader.Themes
    if themes.exists():
        [download_theme(bootloader, theme.name)
            for theme in Path(themes).iterdir() if theme.is_dir()]


'''
SMBIOS
'''
# convert from plist if exists
for smbiosfile in ROOT.glob('*_smbios.plist'):
    with open(smbiosfile, 'rb') as f:
        smbios = plistlib.load(f)
        with open(smbiosfile.name.split('.')[0] + '.json', 'w', encoding='utf8') as out:
            json.dump(smbios, out)
    smbiosfile.unlink()


def gen_smbios():
    '''Generate sn, mlb and smuuid and save to gen_smbios.json
    and set to config file
    '''
    Terminal.title('Generating sn, mlb and smuuid')
    product = PRODUCT
    macserial = ROOT / 'macserial'
    if not macserial.exists():
        download(Urls.MACSERIAL, macserial)
    sn, _, mlb = shout(
        f'{macserial} -m {product} -g -n 1').split(' ')
    smuuid = shout('uuidgen')
    with open('gen_smbios.json', 'w', encoding='utf8') as f:
        json.dump({
            'sn': sn, 'mlb': mlb, 'smuuid': smuuid, 'product': product
        }, f)
    set_configs(f'sn={sn} mlb={mlb} smuuid={smuuid} product={product}')
    return


def set_smbios(smbiosfile):
    with open(smbiosfile, 'r', encoding='utf8') as f:
        smbios = json.load(f)
        kvs = []
        for key in ('sn', 'mlb', 'smuuid', 'product'):
            kvs.append(f'{key}={smbios[key]}')
        set_configs(kvs)


def update_config():
    '''Update clover and oc config
    '''
    patches = []
    for dsl in sorted(ACPI.glob('SSDT-*.dsl')):
        with open(dsl, 'r') as f:
            while True:
                line = f.readline()
                if line and line.startswith('// Patch:'):
                    patches.append(
                        {
                            'Comment': line[9:].strip() + ', pair with ' + name_without_ext(dsl),
                            'Find': Plist.data(f.readline()[8:].strip()),
                            'Replace': Plist.data(f.readline()[11:].strip())
                        }
                    )
                if not line or not line.startswith('//'):
                    break

    if OC.exist:
        # Kexts
        # remove unnecessary kext plugins
        for bootloader in BOOTLOADERS:
            for kext, plugins in KEXT_PLUGINS_TO_DELETE.items():
                _plugins = []
                for plugin in plugins:
                    _plugin = bootloader.Kexts / kext / 'Contents' / 'Plugins' / plugin
                    if _plugin.exists():
                        _plugins.append(plugin)
                    sh('rm -rf', _plugin)
                if _plugins:
                    Terminal.title('Deleting unused kext plugins')
                    Terminal.success(f'{_plugins} in {kext} is deleted')

        kexts = []
        kextpath = OC.Kexts
        for kext in sorted(kextpath.rglob('*.kext')):
            if kext.name[0] == '.':
                continue
            kextinfo = {
                'Enabled': True,
                'BundlePath': kext.relative_to(kextpath).as_posix(),
                'PlistPath': 'Contents/Info.plist'
            }
            executable = '/'.join(('Contents', 'MacOS', kext.name[:-5]))
            if Path(kext, executable).exists():
                kextinfo['ExecutablePath'] = executable
            kexts.append((KEXTS_PRIORITY.get(kext.name, 100), kextinfo))
        kexts = [x[1] for x in sorted(kexts, key=lambda x: x[0])]

    if CLOVER.exist:
        Terminal.title('Updating', CLOVER.config.file)
        _patches = deepcopy(patches)
        for patch in _patches:
            patch['Disabled'] = False
        CLOVER.config.set('ACPI>DSDT>Patches', _patches)
        Terminal.success('config updated')

        theme = CLOVER.config.get('theme')
        if not CLOVER.Themes.exists() or not (CLOVER.Themes / theme).exists():
            set_config(CLOVER, f'theme={theme}')

    if OC.exist:
        Terminal.title('Updating', OC.config.file)
        _patches = deepcopy(patches)
        for patch in _patches:
            patch['Enabled'] = True
        OC.config.set('ACPI>Patch', _patches)
        OC.config.set('ACPI>Add', [{'Enabled': True, 'Path': aml.name}
                                   for aml in sorted(OC.ACPI.glob('SSDT-*.aml'))])
        OC.config.set('Kernel>Add', kexts)
        OC.config.set('UEFI>Drivers', sorted([
            driver.name for driver in (OC.Drivers).glob('*.efi')
        ]))
        Terminal.success('config updated')
    return


def update_acpi():
    acpi = ACPI
    if acpi.exists():
        iasl = acpi / 'iasl'
        if not iasl.exists():
            Terminal.title('Downloading iasl...')
            sh(f'curl -# -R -LOk {Urls.IASL_DOWNLOAD_URL}')
            sh(f'unzip iasl.zip iasl -d {iasl.parent} && rm iasl.zip')
            sh(f'chmod a+x {iasl}')
        sh('rm -rf {}/*.aml'.format(acpi))
        sh(f'{iasl} -oa {acpi}/SSDT-*.dsl')
        for bootloader in BOOTLOADERS:
            if bootloader.exist:
                sh(f'rm -rf {bootloader.ACPI}')
                bootloader.ACPI.mkdir(parents=True)
                sh(f'cp -p {acpi}/SSDT-*.aml {bootloader.ACPI}')


def set_dispaly(resolution):
    scale, dmlr = dict(fhd=('1', 'CgAAAA=='),
                       uhd=('2', 'FAAAAA=='))[resolution]
    set_configs(f'uiscale={scale} dmlr={dmlr}')


def override_edid_for_big_sur():
    Terminal.title(
        'Overriding edid for big sur(force dispaly running at 48Hz)')
    if Terminal.confirm('Do you want to do this'):
        edid = shout('ioreg -lw0 | grep -i "IODisplayEDID"')
        edid = edid.split('<')[1].split('>')[0]
        print('Display EDID:', edid)
        edid = edid[:108] + 'a6a6' + edid[112:]
        data = [int(edid[i:i+2], 16) for i in range(0, len(edid), 2)]
        checksum = hex(256 - sum(data[:-1]) % 256)[2:]
        print('Modified EDID:', edid[:-2] + checksum)
        data[-1] = int(checksum, 16)
        data = b64encode(bytes(data)).decode('utf-8')
        print('data:', data)
        for bootloader in BOOTLOADERS:
            bootloader.config.set('edid', data)


def restore_edid():
    for bootloader in BOOTLOADERS:
        bootloader.config.delete('edid')


def before_release():
    set_smbios(ROOT / 'sample_smbios.json')
    set_configs('bootarg+-v')
    restore_edid()


RELEASE_FILES = 'README.md README_CN.md update.py packages.csv sample_smbios.json ACPI'
INTEL_CARDS = ('AirportItlwm.kext', 'IntelBluetoothFirmware.kext',
               'IntelBluetoothInjector.kext')
BRCM_CARDS = ('AirportBrcmFixup.kext', 'BrcmBluetoothInjector.kext',
              'BrcmFirmwareData.kext', 'BrcmPatchRAM3.kext')


def release(model, target, kexts):
    TMP.mkdir(exist_ok=True)

    bootloaders = ['CLOVER', 'OC']
    for f in RELEASE_FILES.split(' ') + bootloaders:
        sh(f'cp -r', f, TMP)

    for kext in kexts:
        sh(f'rm -rf {TMP}/OC/Kexts/{kext}')
        sh(f'rm -rf {TMP}/CLOVER/kexts/Other/{kext}')

    sh(f'python3 {TMP}/update.py --edid restore')
    sh(f'python3 {TMP}/update.py --config')

    for bootloader in bootloaders:
        sh(f'cd {TMP} && zip -r {bootloader}.zip {bootloader} {RELEASE_FILES}')
        sh(f'cp -r {TMP}/{bootloader}.zip {ROOT}/{model}-{bootloader}-{target}-$(date +%y%m%d).zip')

    sh('rm -rf', TMP)


def after_release():
    set_smbios(ROOT / 'my_smbios.json')
    set_configs('bootarg--v')


def fix_sleep():
    sh('sudo pmset -a hibernatemode 0')
    sh('sudo pmset -a autopoweroff 0')
    sh('sudo pmset -a standby 0')
    sh('sudo pmset -a proximitywake 0')


def done(msg: str = 'Done'):
    update_config()

    for bootloader in BOOTLOADERS:
        bootloader.config.save()

    if not ISWIN:
        sh('dot_clean', ROOT)
        sh('rm -rf ../.Trashes')
        sh('rm -rf', TMP)

    Terminal.success(msg)
    exit()


if __name__ == "__main__":
    TMP.mkdir(exist_ok=True)

    parser = argparse.ArgumentParser(
        description='''Update config''', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--fixsleep', default=False, action='store_true',
                        help='fix sleep issues')
    parser.add_argument('--set', nargs='*', metavar='k=v',
                        help='update config.plist with `k=v` pairs, e.g. bootarg--v uiscale=1')
    parser.add_argument('--acpi', default=False, action='store_true',
                        help='update SSDTs and DSDT/Patches')
    parser.add_argument('--smbios', default=False,
                        help='set/gen smbios, e.g. --smbios my_smbios.json')
    parser.add_argument('--themes', default=False, action='store_true',
                        help='update themes')
    parser.add_argument('--display', default=False,
                        help='fix fhd or uhd display, e.g. --display fhd')
    parser.add_argument('--config', default=False, action='store_true',
                        help='update configs only')
    parser.add_argument('--bigsur', default=False,
                        action='store_true', help='prepare for big sur')
    parser.add_argument('--edid', default=False, help='prepare for big sur')
    parser.add_argument('--release', default=False, help='release')

    args = parser.parse_args()

    if args.set:
        set_configs(args.set)
    elif args.acpi:
        update_acpi()
    elif args.fixsleep:
        fix_sleep()
    elif args.smbios:
        if args.smbios == 'gen':
            gen_smbios()
        else:
            set_smbios(args.smbios)
    elif args.config:
        # update_acpi()
        # update_config()
        pass
    elif args.bigsur:
        override_edid_for_big_sur()
        set_configs('bootarg+-v')
    elif args.edid:
        if args.edid == 'restore':
            restore_edid()
        elif args.edid == '48Hz':
            override_edid_for_big_sur()
    elif args.themes:
        update_themes(CLOVER)
    elif args.display:
        set_dispaly(args.display)
    elif args.release:
        before_release()
        release(args.release, 'INTEL', BRCM_CARDS)
        release(args.release, 'BRCM', INTEL_CARDS)
        # after_release()
    else:
        update_acpi()
        update_themes(CLOVER)
        # update_config()

    done()

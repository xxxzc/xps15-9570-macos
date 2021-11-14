import argparse
import json
import platform
import plistlib
import shutil
import textwrap
from datetime import date
from copy import deepcopy
from os import system as _sh
from pathlib import Path
from subprocess import check_output

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
KEXT_CONFIG = {
    'BlueToolFixup.kext': {
        'MinKernel': '21.0.0'
    },
    'IntelBluetoothInjector.kext': {
        'MaxKernel': '20.99.99',
        'MinKernel': '16.0.0'
    },
    'BrcmBluetoothInjector.kext': {
        'MaxKernel': '20.99.99',
        'MinKernel': '16.0.0'
    }
}

class Urls:
    IASL_DOWNLOAD_URL = 'https://bitbucket.org/RehabMan/acpica/downloads/iasl.zip'
    MACSERIAL = 'https://raw.githubusercontent.com/daliansky/Hackintosh/master/Tools/macserial'
    ONE_KEY_CPUFRIEND = 'https://raw.githubusercontent.com/stevezhengshiqi/one-key-cpufriend/master/one-key-cpufriend.sh'
    UPDATE_PY = 'https://raw.githubusercontent.com/xxxzc/xps15-9570-macos/OC/update.py'


ROOT = Path(__file__).absolute().parent
TMP = ROOT / 'tmp'
ACPI = ROOT / 'ACPI'
PACKAGES_CSV = ROOT / 'packages.csv'


'''
TERMINAL
'''


class Terminal:
    _ERROR = 'x'
    _TITLE = '::'
    _ACTION = '==>'
    _SUCCESS = '√'
    _WARN = '!'

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

    @staticmethod
    def warning(*msg):
        print(Terminal._WARN, *msg)


def darwin(func):
    def inner(*args, **kwargs):
        if platform.system() != 'Darwin':
            Terminal.error(func.__name__, 'only works on macOS.')

        return func(*args, **kwargs)
    return inner


def notwin(func):
    def inner(*args, **kwargs):
        if platform.system() == 'Windows':
            Terminal.error(func.__name__, 'could not work on Windows')
        return func(*args, **kwargs)
    return inner


def sh(*args):
    _sh(' '.join(map(str, args)))


def remove(path: Path):
    '''remove file or dir
    '''
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink()


def shout(cmd) -> str:
    return check_output(cmd, shell=True, encoding='utf-8').strip()


def download(url, path, executable=True):
    path.parent.mkdir(exist_ok=True, parents=True)
    sh(f'curl -fsSL {url} -o {path}')
    if executable:
        sh('chmod +x', path)


'''
CONFIG
'''


class Plist:
    SPLITTER = '>'

    def __init__(self, filepath: Path, keymap: dict):
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
        if s.startswith('0x'):  # '0x191b0000' -> '0x00001b19'
            return bytes.fromhex(''.join(reversed(textwrap.wrap(s[2:], 2))))
        s = ''.join(x for x in s.strip().split(' ') if x)
        if len(s) % 2 == 1:
            s = '0' + s
        return bytes.fromhex(s)

    def real_key(self, key: str) -> list:
        return self.keymap.get(key, key).split(self.SPLITTER)

    def find_key(self, parent, key: str, path=''):
        '''find parent that contains this key, case insensitive
        '''
        key = key.lower()
        for k, v in parent.items():
            if k.lower() == key:
                yield path + self.SPLITTER + k
            elif k[0] == '#' and k[1:].lower() == key:
                parent[k[1:]] = v
                parent.pop(k, 0)
                yield path + self.SPLITTER + k[1:]
            elif type(v) is dict:
                yield from self.find_key(v, key, path+self.SPLITTER+k)
        return ''

    def index(self, key: str):
        '''return real key and the plist that contains this key
        '''
        keys = self.real_key(key)
        parent = self.value
        if len(keys) == 1 and keys[0] == key:
            _key = next(self.find_key(parent, key), '')
            if not _key:
                return None, key
            keys = _key.split(self.SPLITTER)[1:]
        try:
            for k in keys[:-1]:
                parent = parent[k]
        except:
            return None, key
        return parent, keys[-1]

    def get(self, key):
        '''return parent[key]
        '''
        parent, key = self.index(key)
        return parent[key]

    def set(self, key, value):
        '''set plist[key] to value, return key, old value and new value
        '''
        parent, key = self.index(key)

        if not parent:
            Terminal.warning(key, 'not found')
            return

        # prefix '#' -> deleted
        for k, v in parent.items():
            if k[0] == '#' and k[1:] == key:
                parent[k[1:]] = v
                parent.pop(k, 0)
                break

        old = parent.get(key, '' if type(
            value) is str and value.isalpha() else Plist.data(''))

        if type(old) is str or type(value) is not str:
            pass
        else:  # value is str and old value is not str
            if type(old) is bytes:
                value = Plist.data(value)
            elif type(old) is bool:
                value = bool(eval(value.capitalize()))
            elif type(old) is int:
                value = int(value)
            else:
                value = eval(value)

        parent[key] = value
        if type(value) not in (dict, list):
            Terminal.success('Set', key, 'from', old, 'to', value)
        return

    def delete(self, key):
        parent, key = self.index(key)
        if parent and key in parent:
            parent['#'+key] = parent[key]
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


oc_keymap = dict(
    sn='PlatformInfo>Generic>SystemSerialNumber',
    mlb='PlatformInfo>Generic>MLB',
    smuuid='PlatformInfo>Generic>SystemUUID',
    uiscale='UEFI>Output>UIScale',
    bootarg='NVRAM>Add>7C436110-AB2A-4BBB-A880-FE41995C9F82>boot-args',
    timeout='Misc>Boot>Timeout',
    layoutid='DeviceProperties>Add>PciRoot(0x0)/Pci(0x1f,0x3)>layout-id',
    dmlr='DeviceProperties>Add>PciRoot(0x0)/Pci(0x2,0x0)>dpcd-max-link-rate',
    edid='DeviceProperties>Add>PciRoot(0x0)/Pci(0x2,0x0)>AAPL00,override-no-connect',
    properties='DeviceProperties>Add',
    booterquirks='Booter>Quirks',
    product='PlatformInfo>Generic>SystemProductName'
)


OC = Bootloader(ROOT, {}, oc_keymap)

try:
    PRODUCT = OC.config.get('product')
except Exception:
    PRODUCT = 'MacBookPro15,1'


def set_config(kvs):
    '''update config with key=value pairs
    e.g.
    'uiscale=1' for FHD display
    'theme=Nightwish' to set Clover theme
    'bootarg--v bootarg+darkwake=1' to set bootargs
    '''
    bootloader = OC

    if type(kvs) is str:
        kvs = kvs.split(' ')

    config = bootloader.config

    Terminal.title('Setting', config.file)

    bootargs = []
    for kv in kvs:
        if not kv:
            continue

        if kv.startswith('bootarg'):
            bootargs.append(kv)
            continue

        key, value = kv.split('=', 1)
        config.set(key, value)

    if bootargs:
        boot, arg = config.index('bootarg')
        argdict = {}
        for x in boot[arg].split(' '):
            if not x:
                continue
            argdict[x.split('=')[0]] = x

        for bootarg in bootargs:
            key = bootarg[8:].split('=')[0]
            if bootarg[7] == '-':  # delete
                argdict.pop(key, 0)
            else:
                argdict[key] = bootarg[8:]
        boot[arg] = ' '.join(argdict.values())
        Terminal.success('Set bootargs to ', boot[arg])
    return


'''
SMBIOS
'''
# convert from plist if exists
for smbiosfile in ROOT.glob('*_smbios.plist'):
    with open(smbiosfile, 'rb') as f:
        smbios = plistlib.load(f)
        with open(smbiosfile.name.split('.')[0] + '.json', 'w', encoding='utf8') as out:
            json.dump(smbios, out)
    remove(smbiosfile)


@darwin
def get_rom():
    return shout("ifconfig en0 | awk '/ether/{print $2}' | sed -e 's/\://g'")


@darwin
def gen_smbios():
    '''Generate sn, mlb and smuuid and save to gen_smbios.json
    and set to config file
    '''
    Terminal.title('Generating sn, mlb and smuuid')
    if not PRODUCT:
        product = input("please input model, e.g. MacBookPro15,1 :")
    else:
        product = PRODUCT
    macserial = ROOT / 'macserial'
    if not macserial.exists():
        download(Urls.MACSERIAL, macserial)
    sn, _, mlb = shout(
        f'{macserial} -m {product} -g -n 1').split(' ')
    smuuid = shout('uuidgen')
    rom = get_rom()
    with open('gen_smbios.json', 'w', encoding='utf8') as f:
        json.dump({
            'sn': sn, 'mlb': mlb, 'smuuid': smuuid,
            'product': product, 'rom': rom
        }, f)
    set_config(
        f'sn={sn} mlb={mlb} smuuid={smuuid} product={product} rom={rom}')
    return


def set_smbios(smbiosfile):
    with open(smbiosfile, 'r', encoding='utf8') as f:
        smbios = json.load(f)
        kvs = []
        for key in ('sn', 'mlb', 'smuuid', 'product', 'rom'):
            kvs.append(f'{key}={smbios[key]}')
        set_config(kvs)


def show_packages():
    for kext in sorted(OC.Kexts.glob('*.kext')):
        if kext.name[0] == '.':
            continue
        kextversion = shout("grep -A1 -m 2 'CFBundleShortVersionString' " + str(Path(
            kext, 'Contents', 'Info.plist')) + " | awk -F '[<,>]' 'NR>1{print $3}'")
        print(kext.name, kextversion)


def update_config():
    '''Update OC config
    '''
    Terminal.title('Updating', OC.config.file)

    # ACPI patches
    patches = []
    ssdt_comments = {}
    for dsl in sorted(ACPI.glob('SSDT-*.dsl')):
        with open(dsl, 'r') as f:
            ssdt_comments[dsl.name.split('.')[0]] = f.readline()[
                2:].strip()
            while True:
                line = f.readline()
                if line and line.startswith('// Patch:'):
                    patches.append(
                        {
                            'Comment': line[9:].strip() + ', pair with ' + dsl.name.split('.')[0],
                            'Find': Plist.data(f.readline()[8:].strip()),
                            'Replace': Plist.data(f.readline()[11:].strip())
                        }
                    )
                if not line or not line.startswith('//'):
                    break

    if patches:
        _patches = deepcopy(patches)
        for patch in _patches:
            patch['Enabled'] = True
        OC.config.set('ACPI>Patch', _patches)

    # ACPI amls
    OC.config.set('ACPI>Add', [{'Enabled': True, 'Path': aml.name,
                                'Comment': ssdt_comments.get(aml.name.split('.')[0], '')}
                               for aml in sorted(OC.ACPI.glob('SSDT-*.aml'))])

    OC.config.set('UEFI>Drivers', [{'Enabled': True, 'Path': driver.name} 
        for driver in sorted(OC.Drivers.glob('*.efi')) if driver.name[0] != '.'
        ])

    # Kexts
    # remove unnecessary kext plugins
    for kext, plugins in KEXT_PLUGINS_TO_DELETE.items():
        removed = []
        for plugin in plugins:
            plugin = OC.Kexts / kext / 'Contents' / 'PlugIns' / plugin
            if plugin.exists():
                removed.append(plugin)
                remove(plugin)
        if removed:
            Terminal.title('Removing unused kext plugins')
            Terminal.success(f'{removed} in {kext} deleted')

    kexts = []
    kextpath = OC.Kexts
    for kext in sorted(kextpath.rglob('*.kext')):
        if kext.name[0] == '.':
            continue
        kextversion = shout("grep -A1 -m 2 'CFBundleShortVersionString' " + str(Path(
            kext, 'Contents', 'Info.plist')) + " | awk -F '[<,>]' 'NR>1{print $3}'")
        kextinfo = {
            'Enabled': True,
            'BundlePath': kext.relative_to(kextpath).as_posix(),
            'PlistPath': 'Contents/Info.plist',
            'Comment': kextversion or ''
        }
        executable = '/'.join(('Contents', 'MacOS', kext.name[:-5]))
        if Path(kext, executable).exists():
            kextinfo['ExecutablePath'] = executable
        kextinfo.update(KEXT_CONFIG.get(kext.name, {}))
        kexts.append((KEXTS_PRIORITY.get(kext.name, 100), kextinfo))

    kexts = [x[1] for x in sorted(kexts, key=lambda x: x[0])]
    OC.config.set('Kernel>Add', kexts)

    Terminal.success('OC config updated')
    return


@notwin
def update_acpi():
    acpi = OC.ACPI
    iasl = ACPI / 'iasl'
    if not iasl.exists():
        Terminal.title('Downloading iasl...')
        sh(f'curl -# -R -LOk {Urls.IASL_DOWNLOAD_URL}')
        sh(f'unzip iasl.zip iasl -d {iasl.parent} && rm iasl.zip')
        sh(f'chmod a+x {iasl}')
    sh(f'rm -rf {acpi}/*.aml')
    sh(f'{iasl} -oa {acpi}/SSDT-*.dsl')


def set_display(resolution):
    scale, dmlr = dict(fhd=('0', '0A000000'),
                       uhd=('0', '14000000'))[resolution]
    set_config(f'uiscale={scale} dmlr={dmlr}')


def restore_edid():
    OC.config.delete('edid')
    Terminal.success('EDID restored')


RELEASE_FILES = 'README.md README_CN.md ACPI Drivers Kexts Resources config.plist OpenCore.efi update.py sample_smbios.json'.split(
    ' ')
INTEL_CARDS = ('AirportItlwm.kext', 'IntelBluetoothFirmware.kext',
               'IntelBluetoothInjector.kext')
BRCM_CARDS = ('AirportBrcmFixup.kext', 'BrcmBluetoothInjector.kext',
              'BrcmFirmwareData.kext', 'BrcmPatchRAM3.kext')


@notwin
def release(model, target, remove_kexts=[]):
    sh(f'rm -rf {model}-OC-{target}* {TMP}')
    TMP.mkdir(exist_ok=True)
    for f in RELEASE_FILES:
        sh(f'cp -r {f} {TMP}/')
    for kext in remove_kexts:
        remove(TMP/'Kexts'/kext)
    sh(f'python3 tmp/update.py --smbios sample_smbios.json')
    sh(f'python3 tmp/update.py --set bootarg+-v')
    sh(f'python3 tmp/update.py --display uhd')
    zipname = f'{model}-OC-{target}-' + date.today().strftime('%y%m%d')
    sh(f'mv tmp {zipname}')
    sh(f'zip -r {zipname}.zip {zipname}')
    sh(f'rm -rf {zipname}')
    return


@darwin
def fix_sleep():
    sh('sudo pmset -a hibernatemode 0')
    sh('sudo pmset -a autopoweroff 0')
    sh('sudo pmset -a standby 0')
    sh('sudo pmset -a proximitywake 0')


def cleanup():
    if platform.system() == 'Darwin':
        sh('dot_clean', ROOT)
    remove(TMP)


def done(msg: str = 'Done'):
    update_config()
    OC.config.save()
    cleanup()
    Terminal.success(msg)
    exit()


if __name__ == "__main__":
    cleanup()

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
    parser.add_argument('--display', default=False,
                        help='fix fhd or uhd display, e.g. --display fhd')
    parser.add_argument('--config', default=False, action='store_true',
                        help='update configs only')
    parser.add_argument('--release', default=False, help='release')
    parser.add_argument('--list', default=False, action='store_true',
                        help='show packages')
    parser.add_argument('--self', default=False,
                        action='store_true', help='update update.py')

    args = parser.parse_args()

    if args.self:
        download(Urls.UPDATE_PY, ROOT/'update.py', False)
    elif args.set:
        set_config(args.set)
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
        pass
    elif args.display:
        set_display(args.display)
    elif args.release:
        release(args.release, 'INTEL', BRCM_CARDS)
        release(args.release, 'BRCM', INTEL_CARDS)
    elif args.list:
        show_packages()
    else:
        # update_acpi()
        pass
    done()

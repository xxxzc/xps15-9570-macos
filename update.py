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

ISWIN = platform.system() == 'Windows'
CLOVER_THEME_URL = 'git://git.code.sf.net/p/cloverefiboot/themes'
IASL_DOWNLOAD_URL = 'https://bitbucket.org/RehabMan/acpica/downloads/iasl.zip'
MACSERIAL = 'https://raw.githubusercontent.com/daliansky/Hackintosh/master/Tools/macserial'
ONE_KEY_CPUFRIEND = 'https://raw.githubusercontent.com/stevezhengshiqi/one-key-cpufriend/master/one-key-cpufriend.sh'
GITHUB_TOKEN = 'NWFhNjIyNzc0ZDM2NzU5NjM3NTE2ZDg3MzdhOTUyOThkNThmOTQ2Mw=='
DEFAULT_THEME = 'Nightwish'
FOLDER_MAPPER = dict(CLOVER={
    'ACPI': 'ACPI/patched',
    'Kexts': 'kexts/Other',
    'Drivers': 'drivers/UEFI'
}, OC={})
ROOT = Path(__file__).absolute().parent
OC = ROOT / 'OC'
CLOVER = ROOT / 'CLOVER'
TMP = ROOT / 'tmp'
ACPI = ROOT / 'ACPI'
KEXTS = ROOT / 'Kexts'
DRIVERS = ROOT / 'Drivers'
PACKAGES_CSV = ROOT / 'packages.csv'
BOOTLOADERS = []
if CLOVER.exists():
    BOOTLOADERS.append(CLOVER)
if OC.exists():
    BOOTLOADERS.append(OC)

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


'''
Terminal
'''
if ISWIN:
    def colored(text: str, color: int, target='fg'):
        return text
else:
    def colored(text: str, color: int, target='fg'):
        # colored output https://stackoverflow.com/a/56774969
        target = 38 if target == 'fg' else 48
        return f"\33[{target};5;{color}m{text}\33[0m"

PREFIX_TITLE = colored('::', 75)
PREFIX_ACTION = colored('==>', 40)


def Title(*args):
    print(PREFIX_TITLE, *args)


def Prompt(msg: str, force=False) -> str:
    if force:
        return ''
    return input(f"{PREFIX_ACTION} {msg}")


def Confirm(msg: str, force=False) -> bool:
    if force:
        return True
    return Prompt(msg + '?(Y/n)') != 'n'


def sh(*args):
    if ISWIN:
        return
    _sh(' '.join(map(str, args)))


def shout(cmd) -> str:
    '''sh cmd then return output
    '''
    return check_output(cmd, shell=True, encoding='utf-8').strip()


def get_timestamp(path, t='B'):
    ''' 'B' - birth time, 'm' - modified time
    '''
    return int(shout('stat -f%{} {}'.format(t, path)))


def get_folder(folder, bootloader: Path) -> Path:
    folder = bootloader / FOLDER_MAPPER[bootloader.name].get(folder, folder)
    folder.mkdir(exist_ok=True, parents=True)
    return folder


class Plist:
    TYPES = {
        "clover": {
            "identifier": "Boot",
            "keywords": dict(
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
                properties='Devices>Properties',
                booterquirks="Quirks"
            ),
            "copyfrom": {
                "clover": ("sn", "mlb", "smuuid"),
                "oc": ("sn", "mlb", "smuuid", "uiscale",
                       "bootarg", "layoutid", "properties", "booterquirks"),
                "smbios": ("sn", "mlb", "smuuid")
            }
        },
        "oc": {
            "identifier": "Booter",
            "keywords": dict(
                sn='PlatformInfo>Generic>SystemSerialNumber',
                mlb='PlatformInfo>Generic>MLB',
                smuuid='PlatformInfo>Generic>SystemUUID',
                uiscale='NVRAM>Add>4D1EDE05-38C7-4A6A-9CC6-4BCCA8B38C14>UIScale',
                bootarg='NVRAM>Add>7C436110-AB2A-4BBB-A880-FE41995C9F82>boot-args',
                timeout='Misc>Boot>Timeout',
                layoutid='DeviceProperties>Add>PciRoot(0x0)/Pci(0x1f,0x3)>layout-id',
                dmlr='DeviceProperties>Add>PciRoot(0x0)/Pci(0x2,0x0)>dpcd-max-link-rate',
                properties='DeviceProperties>Add',
                booterquirks="Booter>Quirks"
            ),
            "copyfrom": {
                "oc": ("sn", "mlb", "smuuid"),
                "clover": ("sn", "mlb", "smuuid", "uiscale",
                           "bootarg", "layoutid", "properties", "booterquirks"),
                "smbios": ("sn", "mlb", "smuuid")
            }
        },
        "smbios": {
            "identifier": "sn",
            "keywords": {},
            "copyfrom": {}
        }
    }

    def __init__(self, file_path: Path):
        self.file = file_path
        with open(self.file, 'rb') as f:
            self.data = plistlib.load(f)

        self.type = 'plist'
        self.keywords = {}
        self.copyfrom = {}

        for k, v in Plist.TYPES.items():
            if v['identifier'] in self.data:
                self.type = k
                self.keywords = v.get('keywords', {})
                self.copyfrom = v.get('copyfrom', {})
                break

    def save(self):
        with open(self.file, 'wb') as f:
            plistlib.dump(self.data, f)

    def keyword(self, key):
        return self.keywords.get(key, key)

    @staticmethod
    def str2data(b64str: str):
        return b64decode(b64str)

    def get(self, route: str, value_only=False):
        '''Get value from route
        use '>' to split keys
        e.g. PlatformInfo>Generic>SystemSerialNumber
        '''
        keys = self.keyword(route).split('>')
        key = keys.pop(-1)
        parent = self.data
        try:
            for k in keys:
                parent = parent[k]
            return parent[key] if value_only else (parent, key)
        except Exception:
            print(route, "not found!")
            raise

    def set(self, route, value):
        if route == 'uiscale':
            if self.type == 'clover':
                if value in ('Ag==', 'AQ==', b'\x02', b'\x01'):
                    value = '2' if value in ('Ag==', b'\x02') else '1'
            if self.type == 'oc':
                if value in (1, 2, '1', '2'):
                    value = 'Ag==' if str(value) == '2' else 'AQ=='
        parent, key = self.get(route)
        if key not in parent:
            parent[key] = type(value)()
        if type(parent[key]) is bytes and type(value) is not bytes:
            value = Plist.str2data(value)
        else:
            value = type(parent[key])(value)
        parent[key] = value
        if type(value) is bytes:
            value = b64encode(value).decode('utf-8')
        return key, value

    def updatefrom(self, p):
        if not self.file.exists():
            return
        '''update config from other config
        '''
        keys = self.copyfrom.get(p.type, ())
        if self.type == p.type:
            # copy except keys
            print("Update everything from", p.file, "\nExcept:")
            temp = deepcopy(self)
            self.data = deepcopy(p.data)
            for key in keys:
                value = temp.get(key, True)
                self.set(key, value)
                print(f"{key}={value}")
        else:
            # copy keys only
            print('Replace following fields from', p.file)
            for k in keys:
                value = p.get(k, True)
                print(f'Set {k} to {value}')
                self.set(k, value)


OC_CONFIG = Plist(OC / 'config.plist') if OC.exists() else None
CLOVER_CONFIG = Plist(CLOVER / 'config.plist') if CLOVER.exists() else None
CONFIGS = []
if OC_CONFIG:
    CONFIGS.append(OC_CONFIG)
if CLOVER_CONFIG:
    CONFIGS.append(CLOVER_CONFIG)
SAMPLE_SMBIOS_FILE = ROOT / 'smbios.plist'
SAMPLE_SMBIOS = Plist(SAMPLE_SMBIOS_FILE)
MY_SMBIOS_FILE = ROOT / 'my_smbios.plist'
if not MY_SMBIOS_FILE.exists():
    sh(f'cp {SAMPLE_SMBIOS_FILE} {MY_SMBIOS_FILE}')
MY_SMBIOS = Plist(MY_SMBIOS_FILE)


class Package:
    CACHE = dict()  # { url+pattern+version: (rurl, rver) }
    KEYS = 'use,folder,name,target,current,description,pattern,url'
    '''
    packages.csv:
    use,folder,name,target,current,description,pattern,url
    '''

    def __init__(self, **kargs):
        '''Must contain: folder, name, url
        '''
        self.info = kargs
        self.folder = kargs['folder']
        self.name = kargs['name']
        self.url = self.rurl = kargs['url']
        self.use = kargs.get('use', '-')
        self.description = kargs.get('description', '')
        self.pattern = kargs.get('pattern', '.*')
        self.lver = kargs.get('current', 0)  # local version
        self.target = self.rver = kargs.get(
            'target', 'latest')  # remote version

    @property
    def lurl(self):
        return Path(self.folder, self.name)

    def __str__(self):
        return ','.join([self.use, self.folder, self.name,
                         self.target, self.lver, self.description,
                         self.pattern, self.url])

    def update(self, tmp=TMP):
        if self.use == '-':  # not use -> delete if exist
            # sh('rm -rf', self.lurl)
            return True, f'{self.lurl} is deleted'

        # get remote info
        lurl, lver = self.lurl, self.lver
        rurl, rver = self.rurl, self.rver
        changelog = ''

        if rurl == CLOVER_THEME_URL:
            sh(f'cd {lurl.parent.parent} && git archive --remote=git://git.code.sf.net/p/cloverefiboot/themes HEAD themes/{self.name} | tar -x -v')
            self.lver = rver = str(datetime.fromtimestamp(
                get_timestamp(lurl, 'm')).date())
            return True, f'{lurl} is updated to {rver}'

        if lurl.exists() and lver == rver:
            return False, f'{lurl} is update to date'

        domain, user, repo = self.url.split('/')[-3:]
        _info = self.url+self.target+self.pattern
        if _info in Package.CACHE:
            rurl, rver = Package.CACHE[_info]
        elif '.' in self.url.rsplit('/', 1)[-1]:
            # get datetime from remote file
            with urlopen(self.url) as response:
                info = response.info()
                dt = info['last-modified'] or info['date']
                rver = str(datetime.strptime(
                    dt, '%a, %d %b %Y %H:%M:%S %Z').date())
        elif 'github' in domain:
            _tags = 'tags/' if rver != 'latest' else ''
            req = Request(f'https://api.github.com/repos/{user}/{repo}/releases/{_tags}{rver}',
                          headers={'Authorization': 'token {}'.format(b64decode(GITHUB_TOKEN).decode('utf8'))})
            info = json.loads(urlopen(req).read())
            for asset in info['assets']:
                if re.match(self.pattern, asset['name'], re.I):
                    rurl = asset['browser_download_url']
                    rver = info['tag_name']
                    changelog = info['body']
        elif 'bitbucket' in domain:
            req = f'https://api.bitbucket.org/2.0/repositories/{user}/{repo}/downloads'
            info = json.loads(urlopen(req).read())
            for asset in info['values']:
                if re.match(self.pattern, asset['name'], re.I):
                    rdat = asset['created_on'][:10]  # yyyy-mm-dd
                    if rver in ('latest', rdat):  # match version
                        rver = rdat
                        rurl = asset['links']['self']['href']
                        break

        self.rurl = rurl
        self.rver = rver

        Package.CACHE[_info] = (rurl, rver)

        if lurl.exists() and rver == lver:
            return False, f'{lurl} is update to date'

        tmpfile = tmp / rurl.split('/')[-1]
        tmpfolder = Path(tmp, tmpfile.name.split('.')[0])
        if not tmpfile.exists():
            sh(f'curl -# -R -Lk {rurl} -o {tmpfile}')
            if rurl.endswith('.zip'):
                sh(f'unzip -qq -o {tmpfile} -d {tmpfolder}')
            else:
                tmpfolder.mkdir(exist_ok=True)
                sh(f'cp -p {tmpfile} {tmpfolder}')
        lurl.parent.mkdir(exist_ok=True, parents=True)
        sh(f'rm -rf {lurl}')
        for r in tmpfolder.rglob(self.name):
            sh(f'cp -pr {r} {self.folder}')
        self.lver = rver
        msg = f'{lurl} is updated to {rver}'
        if changelog:
            msg += '\nChangelog:\n' + changelog
        return True, msg


def update_packages(packages_csv, force=False):
    '''Update packages and write to
    '''
    packages = []
    with open(packages_csv, 'r') as f:
        keys = f.readline()[:-1].split(',')
        for line in f:
            packages.append(Package(**dict(zip(keys, line[:-1].split(',')))))

    _packages = list(packages)

    if not force:
        print('Packges:')
        for i, p in enumerate(packages, 1):
            print('[{}] {:<46} {} ({})'.format(
                colored(i, 172),
                '/'.join((colored(p.folder, 39), p.name)),
                p.url,
                colored(p.lver if p.lurl.exists() else 'NotInstalled', 204)))

        def get_choices(choice: str) -> set:
            choices = set()
            for c in choice.split(' '):
                if not c:
                    continue
                c = c.split('-') * 2  # fallback
                choices.update(range(int(c[0]), int(c[1]) + 1))
            return choices

        answer = Prompt(
            'Choose update action a(All)/numbers(e.g. 1 3 4-7)/c(Cancel):')
        if answer == 'c':
            packages = []
        elif answer == 'a':
            pass
        else:
            choices = get_choices(answer)
            packages = [p for i, p in enumerate(packages, 1) if i in choices]

    if packages:
        Title('Updating packages...')
        count = 0
        for p in packages:
            success, msg = p.update(TMP)
            if success:
                count += 1
            print(msg)
    else:
        print('nothing to do')

    sync_packages()

    with open(packages_csv, 'w') as f:
        f.write(Package.KEYS + '\n')
        for pkg in _packages:
            f.write(str(pkg) + '\n')


def update_acpi(acpi, force=False):
    if force or Confirm(f'Do you want to compile and update SSDTs in {acpi}'):
        iasl = acpi / 'iasl'
        if not iasl.exists():
            Title('Downloading iasl...')
            sh(f'curl -# -R -LOk {IASL_DOWNLOAD_URL}')
            sh(f'unzip iasl.zip iasl -d {iasl.parent} && rm iasl.zip')
            sh(f'chmod a+x {iasl}')
        sh('rm -rf {}/*.aml'.format(acpi))
        sh(f'{iasl} -oa {acpi}/SSDT-*.dsl')
        for b in BOOTLOADERS:
            folder = get_folder('ACPI', b)
            print(f'Copy SSDTs in {ACPI} to {folder}')
            sh(f'cp -p {ACPI}/SSDT-*.aml {folder}')


def download_theme(theme: Path, force=False):
    theme.parent.mkdir(exist_ok=True)
    if not theme.exists() or force or Confirm('Theme {} exists, do you want to update it'.format(theme.name)):
        Title('Downloading theme', theme.name)
        sh('cd {} && git archive --remote=git://git.code.sf.net/p/cloverefiboot/themes HEAD themes/{} | tar -x -v'.format(
            theme.parent.parent, theme.name))
        print('Theme', theme.name, 'downloaded into', theme.parent)
        print()


def sync_packages(folders=[KEXTS, DRIVERS]):
    Title('Deleting unused ')
    for kext, plugins in KEXT_PLUGINS_TO_DELETE.items():
        _plugins = []
        for plugin in plugins:
            _plugin = KEXTS / kext / 'Contents' / 'Plugins' / plugin
            if _plugin.exists():
                _plugins.append(plugin)
            sh('rm -rf', _plugin)
        if _plugins:
            print(f'{_plugins} in {kext} is deleted')

    Title('Copy packages to OC and CLOVER folder')
    for b in BOOTLOADERS:
        for folder in folders:
            if folder.exists():
                _folder = get_folder(folder.name, b)
                print(f'Copy {folder} to {_folder}')
                sh(f'cp -r {folder}/* {_folder}')


def set_config(config: Plist, kvs):
    '''Update config.plist with key=value pairs
    e.g. 
    'uiscale=1' for FHD display
    'theme=Nightwish' to set Clover theme
    'bootarg--v' to remove -v in bootarg
    'bootarg+darkwake=1' to set darkwake to 1
    '''
    if not config:
        return False
    if type(kvs) is str:
        kvs = kvs.split(' ')
    Title('Setting', config.file)
    bootargs = []
    for kv in kvs:
        if kv.startswith('bootarg'):
            bootargs.append(kv)
            continue
        key, value = kv.split('=', 1)
        if key == 'theme':
            download_theme(CLOVER / 'themes' / value)
        if key == 'smbios':
            smbios = Plist(ROOT / value)
            config.updatefrom(smbios)
            continue
        key, value = config.set(key, value)
        print('Set', config.keyword(key), 'to', value)

    if bootargs:
        boot, key = config.get('bootarg')  # get current
        argdict = dict((ba.split('=')[0], ba) for ba in boot[key].split())
        for ba in bootargs:
            arg = ba[8:].split('=')[0]
            if ba[7] == '-':  # delete
                argdict.pop(arg, 0)
            else:
                argdict[arg] = ba[8:]
        boot[key] = ' '.join(argdict.values())
        print('Set bootargs to ', boot[key])
    config.save()
    return True


def download(url, path, executable=True):
    path.parent.mkdir(exist_ok=True, parents=True)
    sh(f'curl -fsSL {url} -o {path}')
    if executable:
        sh('chmod +x', path)


def gen_smbios():
    '''Generate sn, mlb and smuuid and save to my_smbios.plist
    and set to config file
    '''
    Title('Generating sn, mlb and smuuid')
    product = SAMPLE_SMBIOS.get('product', True)
    macserial = ROOT / 'Tools' / 'macserial'
    if not macserial.exists():
        download(MACSERIAL, macserial)
    sn, s, mlb = shout(
        f'{macserial} -m {product} -g -n 1').split(' ')
    smuuid = shout('uuidgen')
    generated = f'sn={sn} mlb={mlb} smuuid={smuuid}'
    GEN_SMBIOS = ROOT / 'gen_smbios.plist'
    sh('cp', SAMPLE_SMBIOS_FILE, GEN_SMBIOS)
    GEN_SMBIOS = Plist(GEN_SMBIOS)
    print(generated)
    for config in (CLOVER_CONFIG, OC_CONFIG, GEN_SMBIOS):
        set_config(config, generated)


def _update_info(oc_config: Plist = None, clover_config: Plist = None):
    '''Update clover and oc config
    '''
    # ACPI
    patches = []
    for dsl in sorted(ACPI.glob('SSDT-*.dsl')):
        with open(dsl, 'r') as f:
            while True:
                line = f.readline()
                if line.startswith('// Patch:'):
                    patches.append(
                        {
                            'Comment': line[9:].strip(),
                            'Find': Plist.str2data(f.readline()[8:].strip()),
                            'Replace': Plist.str2data(f.readline()[11:].strip())
                        }
                    )
                elif not line:
                    break
    # Kexts
    kexts = []
    kextpath = OC / 'Kexts'
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

    if clover_config:
        Title('Updating', clover_config.file)
        _patches = deepcopy(patches)
        for patch in _patches:
            patch['Disabled'] = False
        clover_config.set('ACPI>DSDT>Patches', _patches)
        print('patches info is updated')

    if oc_config:
        Title('Updating', oc_config.file)
        _patches = deepcopy(patches)
        for patch in _patches:
            patch['Enabled'] = True
        oc_config.set('ACPI>Patch', _patches)
        print('patches info is updated')
        oc_config.set('ACPI>Add', [{'Enabled': True, 'Path': aml.name}
                                   for aml in sorted((OC / 'ACPI').glob('SSDT-*.aml'))])
        print('SSDTs info is updated')
        oc_config.set('Kernel>Add', kexts)
        print('kexts info is updated')
        oc_config.set('UEFI>Drivers', sorted([
            driver.name for driver in (OC / 'Drivers').glob('*.efi')
        ]))
        print('drivers info is updated')


def set_dispaly(resolution):
    _values = dict(fhd=('1', 'CgAAAA=='), uhd=('2', 'FAAAAA=='))
    scale, dmlr = _values[resolution]
    for config in CONFIGS:
        set_config(config, f'uiscale={scale} dmlr={dmlr}')


def release():
    sh(f'rm -rf {ACPI}/*.aml')
    model = SAMPLE_SMBIOS.get('model', True)
    for config in CONFIGS:
        set_config(config, 'smbios=smbios.plist bootarg+-v')
    zip_files = 'ACPI README.md README_CN.md update.py packages.csv smbios.plist'
    for b in BOOTLOADERS:
        sh(f'cd {ROOT} && zip -r {model}-{b.name}-$(date +%y%m%d).zip {b.name} {zip_files}')
    # for config in CONFIGS:
    #     set_config(config, 'smbios=my_smbios.plist bootarg--v')


def update_themes(force=False):
    themes = CLOVER / 'themes'
    if themes.exists():
        [download_theme(theme, force)
            for theme in Path(themes).iterdir() if theme.is_dir()]
    theme = CLOVER_CONFIG.get('GUI>Theme', True)
    theme = themes / theme
    if not theme.exists():
        download_theme(theme, force)


def fix_sleep():
    sh('sudo pmset -a hibernatemode 0')
    sh('sudo pmset -a autopoweroff 0')
    sh('sudo pmset -a standby 0')
    sh('sudo pmset -a proximitywake 0')


def _post_process():
    _update_info(OC_CONFIG, CLOVER_CONFIG)
    if not ISWIN:
        sh('rm -rf', TMP)
        sh('dot_clean', ROOT)
        sh('rm -rf', ROOT.parent / '.Trashes')
    for config in CONFIGS:
        if config:
            config.save()


def Done(msg: str = 'Done'):
    '''Update config and exit
    '''
    _post_process()
    # update_acpi(ACPI, True)
    print(msg)
    exit()


if __name__ == "__main__":
    sh('rm -rf', TMP)
    TMP.mkdir()

    parser = argparse.ArgumentParser(description='''
    Update(download if not exist) kexts, drivers, bootloaders,
        patches, themes and config.''', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--force', default=False, action='store_true',
                        help='force to update without prompt')
    parser.add_argument('--set', nargs='*', metavar='k=v',
                        help='update config.plist with `k=v` pairs, e.g. bootarg--v uiscale=1')
    parser.add_argument('--acpi', default=False, action='store_true',
                        help='update SSDTs and DSDT/Patches')
    parser.add_argument('--fixsleep', default=False, action='store_true',
                        help='fix sleep issues')
    parser.add_argument('--gen', default=False, action='store_true',
                        help='generate SN, MLB and SmUUID')
    parser.add_argument('--smbios', default=False,
                        help='set smbios from plist file, e.g. --smbios my_smbios.plist')
    parser.add_argument('--themes', default=False, action='store_true',
                        help='update themes')
    parser.add_argument('--sync', default=False, action='store_true',
                        help='sync changes in ACPI/Kexts/Drivers to CLOVER/OC')
    parser.add_argument('--config', default=False, action='store_true',
                        help='update configs only')
    parser.add_argument('--display', default=False,
                        help='fix fhd or uhd display, e.g. --display fhd')
    parser.add_argument('--zip', default=False, action='store_true',
                        help='zip CLOVER and OC')

    args = parser.parse_args()

    if args.force:
        update_packages(PACKAGES_CSV, True)
        update_acpi(ACPI, True)
        update_themes(True)
    elif args.set:
        for config in CONFIGS:
            set_config(config, args.set)
    elif args.acpi:
        update_acpi(ACPI)
    elif args.fixsleep:
        fix_sleep()
    elif args.gen:
        gen_smbios()
    elif args.smbios:
        for config in CONFIGS:
            set_config(config, f'smbios={args.smbios}')
    elif args.sync:
        update_acpi(ACPI, True)
        sync_packages([KEXTS, DRIVERS])
        CLOVER_CONFIG.updatefrom(OC_CONFIG)
    elif args.config:
        update_acpi(ACPI, True)
    elif args.themes:
        update_themes()
    elif args.display:
        set_dispaly(args.display)
    elif args.zip:
        release()
    else:
        update_packages(PACKAGES_CSV)
        update_acpi(ACPI)
        update_themes()
    Done()

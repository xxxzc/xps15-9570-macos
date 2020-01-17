import argparse
from pathlib import Path
import plistlib
from os.path import join
from os import system as sh
from datetime import datetime, date
from base64 import b64decode
from subprocess import check_output
from urllib.request import urlopen, Request, urlretrieve
import json
import re

root = Path(__file__).absolute().parent


def R(*args):
    return Path(root, *args)


tmp = R('tmp')  # cache downloaded files
tmp.mkdir(exist_ok=True)


def Done(msg: str = 'Done'):
    print(msg)
    sh('rm -rf {}'.format(tmp))
    exit()


'''
Arguments
'''
parser = argparse.ArgumentParser(description='''
Update(download if not exist) kexts, drivers, bootloaders,
    patches, themes and config.''', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('p', default=root, metavar='PATH/PACKAGE/CONFIG', nargs='?',
                    help='update/download package or packages in this path, e.g. Kexts/ config.plist OpenCore.efi themes/NightWish')
parser.add_argument('--force', default=False, action='store_true',
                    help='force to update without prompt')
parser.add_argument('--set', nargs='*', metavar='k=v',
                    help='update config.plist with `k=v` pairs')
parser.add_argument('--acpi', default=False, action='store_true',
                    help='update SSDTs and DSDT/Patches')
parser.add_argument('--zip', default=False, action='store_true',
                    help='zip folders')
parser.add_argument('--fixsleep', default=False, action='store_true',
                    help='fix sleep issue')
parser.add_argument('--gen', default=False, action='store_true',
                    help='generate SN, MLB and SmUUID')
parser.add_argument('--self', default=False, action='store_true',
                    help='update from https://github.com/xxxzc/xps15-9570-macos/archive/master.zip')

args = parser.parse_args()


if args.fixsleep:
    sh('sudo pmset -a hibernatemode 0')
    sh('sudo pmset -a autopoweroff 0')
    sh('sudo pmset -a standby 0')
    sh('sudo pmset -a proximitywake 0')
    Done()


mappers = dict(CLOVER={
    'ACPI': 'ACPI/patched',
    'Kexts': 'kexts/Other',
    'Drivers': 'drivers/UEFI'
}, OC={})


def c(text, color):
    # colored output https://stackoverflow.com/a/56774969
    return "\33[38;5;{}m{}\33[0m".format(color, text)


PREFIX = c('::', 75)
ARROW = c('==>', 40)


def Title(*args):
    print(PREFIX, *args)


def Prompt(msg: str):
    if args.force:
        return ''
    return input(ARROW + ' ' + msg)


def Confirm(msg: str) -> bool:
    if args.force:
        return True
    r = Prompt(msg + '?(Y/n)')
    return r != 'n'


def shout(cmd):
    return check_output(cmd, shell=True, encoding='utf-8').strip()


def get_timestamp(p, f='B'):
    # 'B' - birth time, 'm' - modified time
    return int(shout('stat -f%{} {}'.format(f, p)))


class Plist:
    clover_keywords = dict(
        sn='SMBIOS>SerialNumber',
        mlb='SMBIOS>BoardSerialNumber',
        smuuid='SMBIOS>SmUUID',
        uiscale='BootGraphics>UIScale',
        theme='GUI>Theme',
        bootarg='Boot>Arguments',
        timeout='Boot>Timeout',
        defaultvolume='Boot>DefaultVolume',
        layoutid='Devices>Properties>PciRoot(0x0)/Pci(0x1f,0x3)>layout-id',
        deviceproperties='Devices>Properties'
    )
    oc_keywords = dict(
        sn='PlatformInfo>Generic>SystemSerialNumber',
        mlb='PlatformInfo>Generic>MLB',
        smuuid='PlatformInfo>Generic>SystemUUID',
        uiscale='NVRAM>Add>4D1EDE05-38C7-4A6A-9CC6-4BCCA8B38C14>UIScale',
        bootarg='NVRAM>Add>7C436110-AB2A-4BBB-A880-FE41995C9F82>boot-args',
        timeout='Misc>Boot>Timeout',
        layoutid='DeviceProperties>Add>PciRoot(0x0)/Pci(0x1f,0x3)>layout-id',
        deviceproperties='DeviceProperties>Add'
    )

    def __init__(self, file):
        self.file = Path(file).absolute()
        with open(file, 'rb') as f:
            self.plist = plistlib.load(f)
        if 'Boot' in self.plist:  # clover
            self.type = 'clover'
            self.keywords = self.clover_keywords
        else:
            self.type = 'oc'
            self.keywords = self.oc_keywords

    def save(self):
        with open(self.file, 'wb') as f:
            plistlib.dump(self.plist, f)

    def keyword(self, key):
        return self.keywords.get(key, key)

    @staticmethod
    def data(b64str):
        return b64decode(b64str)

    def get(self, key, value=False):
        key = self.keyword(key)
        ks = key.split('>')
        item = self.plist
        for k in ks[:-1]:
            item = item[k]
        return item[ks[-1]] if value else (item, ks[-1])

    def set(self, key, value):
        item, key = self.get(key)
        if type(item[key]) is bytes:
            if type(value) is not bytes:
                value = Plist.data(value)
        else:
            value = type(item[key])(value)
        item[key] = value

    def copy(self, another):
        if self.type == another.type:
            Title('Replace everything from',
                  another.file, '\nExcept:')
            for key in self.keywords.values():
                value = self.get(key, True)
                another.set(key, value)
                print('{}={}'.format(key, value))
            self.plist = another.plist
        else:
            Title('Replace following fields from', another.file)
            for k in self.keywords.keys():
                i1, k1 = self.get(self.keywords[k])
                value = another.get(another.keywords[k])
                print('Set {} to {}'.format(k1, value))
                i1[k1] = value
        return self


# cache remote info - { url+pattern+version: (rurl, rver, rdat) }
remote_infos = dict()


class Package:
    # access only, 5000/hr
    GITHUB_TOKEN = 'NWFhNjIyNzc0ZDM2NzU5NjM3NTE2ZDg3MzdhOTUyOThkNThmOTQ2Mw=='

    def __init__(self, **kargs):
        self.__dict__.update(kargs)
        self.changelog = ''

    @property
    def lurl(self):
        return Path(self.folder, self.name)

    def check_update(self):
        # get local info
        lurl, lver, ldat = self.lurl, 'NotInstalled', None
        if lurl.exists():
            ldat = datetime.fromtimestamp(
                get_timestamp(lurl, 'B'))  # B -- birthdate
            lver = ldat.strftime('%y%m%d')
            if lurl.name.endswith('.kext'):
                lver += '(' + shout("grep -A1 -m 2 'CFBundleShortVersionString' " + str(Path(
                    lurl, 'Contents', 'Info.plist')) + " | awk -F '[<,>]' 'NR>1{print $3}'") + ')'

        self.__dict__.update(dict(lver=lver, ldat=ldat))

        # get remote info
        rurl, rver, rdat = self.url, self.version, date.today()

        if lver.split('(')[-1].startswith(rver):
            return False

        _info = self.url+self.version+self.pattern
        if _info in remote_infos:
            rurl, rver, rdat = remote_infos[_info]
        elif 'github' in rurl or 'bitbucket' in rurl:
            domain, user, repo = rurl.split('/')[-3:]
            isgithub = 'github' in domain
            if isgithub:
                req = Request('https://api.github.com/repos/{}/{}/releases/{}'.format(
                    user, repo, 'tags/' + rver if rver != 'latest' else rver),
                    headers={'Authorization': 'token {}'.format(b64decode(self.GITHUB_TOKEN).decode('utf8'))})
            else:
                req = 'https://api.bitbucket.org/2.0/repositories/{}/{}/downloads'.format(
                    user, repo)
            info = json.loads(urlopen(req).read())
            for asset in info['assets' if isgithub else 'values']:
                if re.match(self.pattern, asset['name'], re.I):
                    if isgithub:
                        rurl = asset['browser_download_url']
                        rver = info['tag_name']
                        rdat = asset['updated_at']
                        self.changelog = info['body']
                    else:
                        rdat = asset['created_on']
                        if rver in ('latest', rdat[:10]):
                            rurl = asset['links']['self']['href']
                    break

            rdat = datetime.fromisoformat(rdat[:19])
            rver = rdat.strftime('%y%m%d') + '(' + rver + ')'

        self.__dict__.update(dict(rurl=rurl, rver=rver, rdat=rdat))
        remote_infos[_info] = (rurl, rver, rdat)

        if not ldat:  # not exist
            return True
        if lver.split('(')[-1] == rver.split('(')[-1]:
            return False
        return abs((rdat - ldat).days) > 1

    def update(self, tmp=Path(__file__).parent.joinpath('tmp')):
        tmpfile = tmp / self.rurl.split('/')[-1]
        tmpfolder = Path(tmp, tmpfile.name.split('.')[0])
        if not tmpfile.exists():
            print('Downloading', self.lurl, 'from', self.rurl)
            sh('curl -# -R -Lk {} -o {}'.format(self.rurl, tmpfile))
            if self.rurl.endswith('.zip'):
                sh('unzip -qq -o {} -d {}'.format(tmpfile, tmpfolder))
            else:
                tmpfolder.mkdir(exist_ok=True)
                sh('cp -p {} {}'.format(tmpfile, tmpfolder))
        self.folder.mkdir(exist_ok=True, parents=True)
        sh('rm -rf {}'.format(self.lurl))
        for r in tmpfolder.rglob(self.name):
            sh('cp -pr {} {}'.format(r, self.folder))


def download_theme(theme: Path):
    if not theme.exists() or Confirm('Theme {} exists, do you want to update it'.format(theme.name)):
        Title('Downloading theme', theme.name)
        sh('cd {} && git archive --remote=git://git.code.sf.net/p/cloverefiboot/themes HEAD themes/{} | tar -x -v'.format(
            theme.parent.parent, theme.name))
        Title('Theme', theme.name, 'downloaded into', theme.parent)
        print()


def update_themes(themes):
    if themes.exists():
        [download_theme(theme)
         for theme in Path(themes).iterdir() if theme.is_dir()]
    else:
        themes.mkdir()
        download_theme(Path(themes, 'Nightwish'))


def set_config(configfile: Path, kvs: list):
    '''Update config.plist with key=value pairs
    e.g. 
    'uiscale=1' for FHD display
    'theme=Nightwish' to set Clover theme
    'bootarg--v' to remove -v in bootarg
    'bootarg+darkwake=1' to set darkwake to 1
    '''
    if not configfile.exists() or not configfile.name.endswith('.plist'):
        return False

    Title('Setting', configfile)

    config = Plist(configfile)
    # process bootargs
    bootargs = []
    for kv in kvs:
        if kv.startswith('bootarg'):
            bootargs.append(kv)
        else:
            k, v = kv.split('=', 1)
            if k not in config.keywords:
                print(k, 'field not found.')
                continue

            if k == 'theme':
                theme = R('CLOVER', 'themes', v)
                if not theme.exists():
                    download_theme(theme)

            config.set(k, v)
            print('Set', config.keyword(k), 'to', v)

    if bootargs:
        boot, key = config.get('bootarg')
        argdict = dict((ba.split('=')[0], ba) for ba in boot[key].split())
        for ba in bootargs:
            arg = ba[8:].split('=')[0]
            if ba[7] == '-':
                argdict.pop(arg, 0)
            else:
                argdict[arg] = ba[8:]
        boot[key] = ' '.join(argdict.values())
        print('Boot Args:', boot[key])

    config.save()
    return True


def update_packages(packages):
    '''Updating packages
    '''
    Title('Checking updates...')
    updates = []
    for i, package in enumerate(packages, 1):
        print('({}/{}) {:<46}'.format(i, len(packages), package.name), end='\r')
        if package.check_update():
            updates.append(package)
    packages = updates
    if not packages:
        print('Everything is up-to-date')
        return []
    '''
    Show updates
    '''
    Title(len(packages), 'packages to update')
    for i, p in enumerate(packages, 1):
        print('[{}] {:<46} {} -> {}'.format(
            c(i, 172), '/'.join((c(p.folder, 39), p.name)),
            c(p.lver, 204), c(p.rver, 70)))
        print(c(p.rurl, 245))
        print(c(p.changelog.strip(), 245))

    def get_choices(choice: str) -> set:
        choices = set()
        for c in choice.split(' '):
            if not c:
                continue
            c = c.split('-') * 2  # fallback
            choices.update(range(int(c[0]), int(c[1]) + 1))
        return choices

    if not args.force:
        choices = get_choices(
            Prompt('Enter package(s) number you don\'t want to update (e.g. 1 3 4-7):'))
        if choices:
            packages = [p for i, p in enumerate(packages, 1)
                        if i not in choices]

    if not packages:
        print('Nothing to do')
        return []
    Title('Updating...')
    [p.update() for p in packages]

    return packages


def patching(kexts: Path):
    Title('Set delay after typing to 50ms')
    info = Plist(kexts / 'VoodooI2CHID.kext' / 'Contents' / 'Info.plist')
    info.set('IOKitPersonalities>VoodooI2CHIDDevice Precision Touchpad HID Event Driver>QuietTimeAfterTyping', 50)
    info.save()
    Title('Delete VoodooPS2Mouse.kext and VoodooPS2Trackpad.kext')
    for kext in ('VoodooPS2Mouse.kext', 'VoodooPS2Trackpad.kext'):
        sh('rm -rf {}'.format(kexts / 'VoodooPS2Controller.kext' /
                              'Contents' / 'PlugIns' / kext))


def replace_with_release(folder: Path, version='latest'):
    '''folder is CLOVER/OC
    '''
    # backup your config
    originconfig = folder / 'config.plist'
    backupconfig = R(folder.name + '.plist')
    originthemes = folder / 'themes'
    backupthemes = R('themes')
    if originconfig.exists():
        sh('mv {} {}'.format(originconfig, backupconfig))
    if originthemes.exists():
        sh('mv {} {}'.format(originthemes, backupthemes))

    sh('rm -rf {}'.format(folder))
    if update_packages([Package(
            name=folder.name, folder=root,
            url='https://github.com/xxxzc/xps15-9570-macos',
            description=folder.name + ' Configuration for XPS15-9570',
            version=version, pattern='.*-' + folder.name)]):
        if backupconfig.exists():
            originconfig = Plist(originconfig)
            Plist(backupconfig).copy(originconfig)
            originconfig.save()
        if backupthemes.exists():
            sh('rm -rf {}'.format(originthemes))
            sh('mv {} {}'.format(backupthemes, originthemes))

    sh('rm -f {}'.format(backupconfig))
    sh('rm -f {}'.format(backupthemes))


def update_acpi(ACPI: Path, folders):
    def compile_ssdts(folder: Path):
        # compile if .aml not exist
        ssdts = []
        for dsl in folder.rglob('SSDT-*.dsl'):
            aml = Path(dsl.parent, dsl.name.replace('.dsl', '.aml'))
            if not aml.exists() or get_timestamp(dsl, 'm') > get_timestamp(aml, 'm'):
                ssdts.append((dsl, aml))
        iasl = folder / 'iasl'
        if not iasl.exists():
            Title('Downloading iasl...')
            sh('curl -# -R -LOk https://bitbucket.org/RehabMan/acpica/downloads/iasl.zip')
            sh('unzip iasl.zip iasl -d {} && rm iasl.zip'.format(iasl.parent))
            sh('chmod a+x {}'.format(iasl))
        for (dsl, aml) in ssdts:
            sh('{} -oa {}'.format(iasl, dsl))
        return ssdts

    def get_patches(ACPI: Path):
        '''Get patches from dsl files
        // Patch: xxx
        // Find: ABC
        // Replace: DEF
        '''
        patches = []
        for dsl in Path(ACPI).rglob('SSDT-*.dsl'):
            with open(dsl, 'r') as f:
                while True:
                    line = f.readline()
                    if line.startswith('// Patch:'):
                        patches.append(
                            {
                                'Comment': line[9:].strip(),
                                'Find': Plist.data(f.readline()[8:].strip()),
                                'Replace': Plist.data(f.readline()[11:].strip())
                            }
                        )
                    elif not line:
                        break
        return patches

    patches = sorted(get_patches(ACPI), key=lambda x: x['Comment'])

    Title('Updating SSDTs')
    if ACPI == root:  # do a full update
        sh('rm -rf {}/*.aml'.format(ACPI))
    ssdts = compile_ssdts(ACPI)  # [(dsl, aml), ...]
    for folder in folders:
        if not folder.exists():
            continue
        patches = get_patches(ACPI)
        acpi = folder / mappers[folder.name].get('ACPI', 'ACPI')
        sh('rm -rf {}'.format(acpi))
        acpi.mkdir(exist_ok=True, parents=True)
        sh('cp -p {}/SSDT-*.aml {}'.format(ACPI, acpi))
        config = Plist(folder / 'config.plist')
        if folder == CLOVER:
            for patch in patches:
                patch['Disabled'] = False
            config.plist['ACPI']['DSDT']['Patches'] = patches
        else:
            for patch in patches:
                patch['Enabled'] = True
            config.plist['ACPI']['Patch'] = patches
            config.plist['ACPI']['Add'] = [{'Enabled': True, 'Path': aml.name}
                                           for aml in sorted((folder / 'ACPI').glob('SSDT-*.aml'))]
        config.save()
        print(folder, 'patches updated')


def update_oc_info(folder: Path):
    '''Updating patches, kexts and drivers info for OpenCore
    '''

    config = Plist(folder / 'config.plist')

    config.plist['ACPI']['Add'] = [{'Enabled': True, 'Path': aml.name}
                                   for aml in sorted((folder / 'ACPI').glob('SSDT-*.aml'))]

    kexts = []
    kextpath = folder / 'Kexts'
    prioritys = {
        'Lilu.kext': 0, 'VirtualSMC.kext': 10, 'AppleALC.kext': 20,
        'VoodooGPIO.kext': 30, 'VoodooI2CServices.kext': 35,
        'VoodooI2C.kext': 40, 'VoodooI2CHID.kext': 50,
        'CPUFriend.kext': 21, 'CPUFriendDataProvider.kext': 22,
    }
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
        kexts.append((prioritys.get(kext.name, 100), kextinfo))

    config.plist['Kernel']['Add'] = [x[1] for x in sorted(
        kexts, key=lambda x: x[0])]
    print('Kexts info updated')

    config.plist['UEFI']['Drivers'] = sorted([
        driver.name for driver in (folder / 'Drivers').glob('*.efi')
    ])
    print('Drivers info updated')

    config.save()
    return


if __name__ == '__main__':
    path = Path(args.p).absolute()

    CLOVER, OC = R('CLOVER'), R('OC')
    folders = []
    if path == root:
        folders = [folder for folder in (CLOVER, OC) if folder.exists()]
    elif path == CLOVER or CLOVER in path.parents:
        folders = [CLOVER]
    elif path == OC or OC in path.parents:
        folders = [OC]

    if args.zip:
        sh('rm -rf {}/*.aml'.format(R('ACPI')))
        for folder in folders:
            set_config(folder / 'config.plist',
                       'sn=C02WVDY3KGYG mlb=C028248024NJP4FA8 smuuid=C167D3A2-CC13-4041-8CED-553D772C0749 bootarg+-v'.split(' '))
            sh('cd {} && zip -r XPS15-9570-{}-$(date +%y%m).zip {} README.md update.py packages.csv'.format(
                root, folder.name, folder.name))
        Done()

    if args.gen:
        macserial = R('macserial')
        if not macserial.exists():
            update_packages([
                Package(
                    name='macserial', folder=root,
                    description='', version='latest',
                    pattern='.*-mac', url='https://github.com/acidanthera/MacInfoPkg'
                )
            ])
        sn, s, mlb = shout(
            '{} -m MacBookPro15,1 -g -n 1'.format(macserial)).split(' ')
        uuid = shout('uuidgen')
        for folder in folders:
            set_config(folder / 'config.plist',
                       'sn={} mlb={} smuuid={}'.format(sn, mlb, uuid).split(' '))
        Done()

    '''
    update ACPI, packages.csv and update.py from repo
    '''
    if args.self:
        sh('curl -# -LOk https://github.com/xxxzc/xps15-9570-macos/archive/master.zip')
        sh('unzip {} -d {}'.format('master.zip', root))
        master = R('xps15-9570-macos-master')
        for folder in folders:
            config = folder / 'config.plist'
            if config.exists():
                masterconfig = Plist(master / folder.name / 'config.plist')
                Plist(config).copy(masterconfig)
                masterconfig.save()
            else:
                sh('rm -rf {}'.format(master / folder.name))
        sh('cp -pr {}/* {}'.format(master, root))
        update_acpi(R('ACPI'), folders)
        if R('OC').exists():
            update_oc_info(R('OC'))
        sh('rm -rf {} {}'.format('master.zip', master))
        Done()

    if args.acpi:
        acpi = R('ACPI')
        update_acpi(acpi, (CLOVER, OC))
        Done()

    '''
    Set config.plist
    '''
    if args.set:  # set config
        if path.name.endswith('.plist'):
            set_config(path, args.set)
        else:
            for folder in folders:
                set_config(folder / 'config.plist', args.set)
        Done()

    '''
    Replace current configuration with release
    '''
    # if args.release:
    #     for folder in folders:
    #         replace_with_release(folder, args.release)
    #     Done()

    '''
    Update themes
    '''
    if path.name == 'themes':
        update_themes(path)
        Done()
    elif path.parent.name == 'themes':
        download_theme(path)
        Done()
    elif path.name == 'CLOVER' or (path == root and CLOVER.exists()):
        update_themes(CLOVER / 'themes')

    '''
    Update packages
    '''
    keyword = ''
    if path.name in ('Kexts', 'kexts', 'Other'):
        keyword = 'kext'
    elif path.name in ('Drivers', 'drivers', 'UEFI'):
        keyword = 'driver'

    for folder in folders:
        name = folder.name
        mapper = mappers[name]
        other = 'CLOVER' if name == 'OC' else 'OC'
        packages = []
        with open(R('packages.csv'), 'r') as f:
            keys = f.readline()[:-1].lower().split(',')
            for x in f:
                package = Package(**dict(zip(keys, x[:-1].split(','))))
                pf = package.folder

                if pf[0] == '#':  # remove this
                    for r in folder.rglob(package.name):
                        print('Remove {}'.format(r))
                        sh('rm -rf {}'.format(r))
                    continue

                if package.name == path.name:
                    package.folder = path.parent
                    packages = [package]
                    break

                if pf.startswith(other) or keyword not in pf.lower():
                    continue

                if pf.startswith(name):
                    package.folder = R(pf)
                else:
                    package.folder = folder / mapper.get(pf, pf)

                packages.append(package)

        if packages and Confirm('Do packages update for ' + folder.name):
            update_packages(packages)

        patching(folder / mapper.get('Kexts', 'Kexts'))

    if OC in folders:
        update_oc_info(OC)

    Done()

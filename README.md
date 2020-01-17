## Configuration

| Model     | MacBookPro15,1               | Version        | 10.15.2 19C57       |
| --------- | :--------------------------- | -------------- | ------------------- |
| Processor | Intel Core i5-8300H/i7-8750H | Graphics       | UHD Graphics 630    |
| Memory    | Micron 2400MHz DDR4 8GB x2   | Disk           | Samsung PM961 512GB |
| Audio     | Realtek ALC298               | WiFi/Bluetooth | Dell Wireless 1830  |
| Display   | Sharp LQ156D1 UHD            | Monitor        | HKC GF40 FHD 144Hz  |

### Not Working

- Bluetooth may not work
- Thunderbolt
- SD Card
- Discrete GPU
- Fingerpint

## Installation

**Please download [the latest release](https://github.com/xxxzc/xps15-9570-macos/releases/latest).**

You may refer to [[EN] bavariancake/XPS9570-macOS](https://github.com/bavariancake/XPS9570-macOS) and [[CN] LuletterSoul/Dell-XPS-15-9570-macOS-Mojave](https://github.com/LuletterSoul/Dell-XPS-15-9570-macOS-Mojave) for the installation guide and solutions to some common issues.

But note that please create an issue **in this repository** if you encounter any problem when **using this config** (Please don't disturb others). My writing in English is poooooor:(, but I can read :).

### Headphone

~~@qeeqez found layout-id 30 is good to drive headphone without PluginFix([Overall Audio State](https://github.com/daliansky/XiaoMi-Pro/issues/96)), and it also works for me.~~ 

After updating to 10.15.1, headphone will be distorted after a few minutes in battery mode. 

You have to install [ComboJack](https://github.com/hackintosh-stuff/ComboJack/tree/master/ComboJack_Installer):

1. remove CodecCommander.kext and uninstall ALCPlugFix
2. put VerbStub.kext in kext folder
3. set layout-id to 72 
4. run install.sh

### Sleep Wake

```shell
sudo pmset -a hibernatemode 0
sudo pmset -a autopoweroff 0
sudo pmset -a standby 0
sudo pmset -a proximitywake 0
sudo pmset -b tcpkeepalive 0 (optional)
```

> `-b` - Battery `-c` - AC Power `-a` - Both

Please uncheck all options (except `Prevent computer from sleeping...`, which is optional) in the `Energy Saver` panel.

### SN MLB SmUUID

Please use your own SN, MLB (use [MacInfoPkg](https://github.com/acidanthera/MacInfoPkg) or Clover Configurator or [Hackintool](https://www.tonymacx86.com/threads/release-hackintool-v2-8-6.254559/)) and SmUUID.

```sh
python update.py --set sn=xxx mlb=yyy smuuid=zzz
python update.py --gen # generate and use new SN, MLB and SmUUID
```

As for SmUUID, **please use your Windows system UUID**: run  `wmic csproduct get UUID` in CMD, because OpenCore will use SystemUUID you set in OC/config.plist to boot Windows.

### Touchpad

Touchpad can run in two modes:

1. GPIO mode with SSDT-TPDX.aml

   1\~2% kernel_task cpu usage when idle but cause 10\~30% cpu usage when touchpad is in use

2. Polling mode without SSDT-TPDX.aml

   always 10~15% kernel_task cpu usage

### FHD Display

If you are using FHD(1080p) display, you may want to enable font smoothing:

```
defaults write -g CGFontRenderingFontSmoothingDisabled -bool NO
```

If your laptop display is 1080p, you should set uiscale to 1 and remove `-igfxmlr` in boot arguments:

```sh
python update.py --set uiscale=1 bootarg--igfxmlr
```

### CLOVER Theme

You can set theme to one of these [themes](https://sourceforge.net/p/cloverefiboot/themes/ci/master/tree/themes/).

```sh
python update.py --set theme=xxx # will download if not exist
```

### NTFS Writing

Add `UUID=xxx none ntfs rw,auto,nobrowse` to `/etc/fstab`, **xxx** is the UUID of your NTFS partition. 

If your NTFS partition has Windows installed, you need to run `powercfg -h off`  in powershell in Windows to disable hibernation.

### Tap Delay

- Turn off `Enable dragging` or use `three finger drag` to avoid one-finger tap delay.
- Turn off `Smart zoom` to avoid two-finger tap delay.

See [is-it-possible-to-get-rid-of-the-delay-between-right-clicking-and-seeing-the-context-menu](https://apple.stackexchange.com/a/218181)

## Credits

- [acidanthera](https://github.com/acidanthera) for providing almost all kexts and drivers
- [alexandred](https://github.com/alexandred) for providing VoodooI2C
- [headkaze](https://github.com/headkaze) for providing the very useful [Hackintool](https://www.tonymacx86.com/threads/release-hackintool-v2-8-6.254559/)
- [daliansky](https://github.com/daliansky) for providing the awesome hotpatch guide [OC-little](https://github.com/daliansky/OC-little/) and the always up-to-date hackintosh solutions [XiaoMi-Pro-Hackintosh](https://github.com/daliansky/XiaoMi-Pro-Hackintosh) [黑果小兵的部落阁](https://blog.daliansky.net/)
- [RehabMan](https://github.com/RehabMan) for providing numbers of [hotpatches](https://github.com/RehabMan/OS-X-Clover-Laptop-Config/tree/master/hotpatch) and hotpatch guides
- [knnspeed](https://www.tonymacx86.com/threads/guide-dell-xps-15-9560-4k-touch-1tb-ssd-32gb-ram-100-adobergb.224486) for providing Combojack, well-explained hot patches and USB-C hotplug solution
- [bavariancake](https://github.com/bavariancake/XPS9570-macOS) and [LuletterSoul](https://github.com/LuletterSoul/Dell-XPS-15-9570-macOS-Mojave) for providing detailed installation guide and configuration for XPS15-9570
- And all other authors that mentioned or not mentioned in this repo
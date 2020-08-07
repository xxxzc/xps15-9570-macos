中文 README 请看 [README_CN.md](README_CN.md)

## Configuration

| Model     | XPS15-9570/MacBookPro15,1    | Version        | 10.15.6 19G73       |
| :-------- | :--------------------------- | :------------- | :------------------ |
| Processor | Intel Core i5-8300H/i7-8750H | Graphics       | UHD Graphics 630    |
| Memory    | Micron 2400MHz DDR4 8GB x2   | Storage        | Samsung PM961 512GB |
| Audio     | Realtek ALC298               | WiFi/Bluetooth | Dell Wireless 1830  |
| Display   | Sharp LQ156D1 UHD            | Monitor        | HKC GF40 FHD 144Hz  |

### Not Working

- DiscreteGPU
- Thunderbolt
- Fingerprint
- SD Card (You can try [Sinetek-rtsx](https://github.com/cholonam/Sinetek-rtsx))
- Bluetooth may not work ([explain](https://github.com/xxxzc/xps15-9570-macos/issues/26))

## Installation

**Please use [the latest release](https://github.com/xxxzc/xps15-9570-macos/releases/latest).** 

Try not to use *Clover Configurator* or *OC Configurator* to open config, code editor is a better choice.

If you changed ACPI/Kexts/Drivers, you can run `python3 update.py --sync` to apply these changes to OC and CLOVER, and it will update these infos to config.plist.

You may refer to [[EN] bavariancake/XPS9570-macOS](https://github.com/bavariancake/XPS9570-macOS) and [[CN] LuletterSoul/Dell-XPS-15-9570-macOS-Mojave](https://github.com/LuletterSoul/Dell-XPS-15-9570-macOS-Mojave) for the installation guide and solutions to some common issues.

But note that please create an issue **in this repository** if you encounter any problem when **using this config** (Please don't disturb others). My writing in English is poooooor:(, but I can read :).

### FHD Display

If your laptop display is 1080p, you have to modify your config.plist:

- Find `uiscale` and change its value to `1`  for CLOVER and `AQ==` for OC

- Find `dpcd-max-link-rate` and change its value to `CgAAAA==`

Or simply run `python3 update.py --display fhd`.

## Post Installation

### Silent Boot

Remove `-v` in boot-args to turn off verbose mode(printing boot messages on screen).

```python
python3 update.py --set bootarg--v
```

### Headphone

~~@qeeqez found layout-id 30 is good to drive headphone without PluginFix([Overall Audio State](https://github.com/daliansky/XiaoMi-Pro/issues/96)), and it also works for me.~~ 

After updating to 10.15, headphone will be distorted after a few minutes in battery mode. 

You have to install [ComboJack](https://github.com/hackintosh-stuff/ComboJack/tree/master/ComboJack_Installer) (run install.sh).

### Sleep Wake

Please run following commands:

```shell
sudo pmset -a hibernatemode 0
sudo pmset -a autopoweroff 0
sudo pmset -a standby 0
sudo pmset -a proximitywake 0
```

 or simply run `python3 update.py --fixsleep`.

Please uncheck all options (except `Prevent computer from sleeping...`, which is optional) in the `Energy Saver` panel.

### SN MLB SmUUID

Please use your own SN, MLB and SmUUID, you can copy [smbios.plist](./smbios.plist) to a new one and change `sn, mlb and smuuid` fields to your own, then run `python3 update.py --smbios xxx.plist` to use them, `xxx.plist` is your plist file to store those values. 

If you don't have those values, you can run `python3 update.py --gen` to generate them(will saved to both `gen_smbios.plist` and config file) if you don't have them.

Highly recommend you to use  **Windows system UUID** as SmUUID: run  `wmic csproduct get UUID` in Windows CMD.

### Font Smoothing

If you are using FHD(1080p) display, you may want to enable font smoothing:

```sh
defaults write -g CGFontRenderingFontSmoothingDisabled -bool NO # YES to disable
```

### CLOVER Theme

You can set theme to one of these [themes](https://sourceforge.net/p/cloverefiboot/themes/ci/master/tree/themes/).

```sh
python3 update.py --set theme=xxx # will download if not exist
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
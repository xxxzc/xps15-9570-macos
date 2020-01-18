// Enable GPIO pining for touchpad and disable I2C0
// References:
// [1] https://github.com/xxxzc/xps15-9550-macos/issues/26#issuecomment-546838295
// [2] https://github.com/daliansky/OC-little/tree/master/09-OCI2C-TPXX%E8%A1%A5%E4%B8%81%E6%96%B9%E6%B3%95
// [3] https://github.com/alexandred/VoodooI2C/blob/master/Documentation/GPIO%20Pinning.md

DefinitionBlock ("", "SSDT", 2, "hack", "TPDX", 0x00000000)
{
    External (TPLM, FieldUnitObj)
    External (TPDM, FieldUnitObj)
    External (PKG3, MethodObj)
    External (_SB.PCI0.I2C0, DeviceObj)
    External (SSH0, FieldUnitObj)
    External (SSL0, FieldUnitObj)
    External (SSD0, FieldUnitObj)
    External (FMH0, FieldUnitObj)
    External (FML0, FieldUnitObj)
    External (FMD0, FieldUnitObj)
    External (_SB.PCI0.I2C1, DeviceObj)
    External (SSH1, FieldUnitObj)
    External (SSL1, FieldUnitObj)
    External (SSD1, FieldUnitObj)
    External (FMH1, FieldUnitObj)
    External (FML1, FieldUnitObj)
    External (FMD1, FieldUnitObj)

    Scope (\)
    {
        If (_OSI ("Darwin"))
        {
            TPLM = Zero // touchscreen
            TPDM = Zero // touchpad
        }
    }
    
    // bus configuration for I2C0
    Scope (_SB.PCI0.I2C0)
    {
        Method (SSCN, 0, NotSerialized)
        {
            Return (PKG3 (SSH0, SSL0, SSD0))
        }

        Method (FMCN, 0, NotSerialized)
        {
            Return (PKG3 (FMH0, FML0, FMD0))
        }
    }
    
    // bus configuration for I2C1
    Scope (_SB.PCI0.I2C1)
    {
        Method (SSCN, 0, NotSerialized)
        {
            Return (PKG3 (SSH1, SSL1, SSD1))
        }

        Method (FMCN, 0, NotSerialized)
        {
            Return (PKG3 (FMH1, FML1, FMD1))
        }
    }
}

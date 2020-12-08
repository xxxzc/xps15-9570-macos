// Enable touchpad and touchscreen
// References:
// [1] https://github.com/xxxzc/xps15-9550-macos/issues/26#issuecomment-546838295
// [2] https://github.com/daliansky/OC-little/tree/master/09-OCI2C-TPXX%E8%A1%A5%E4%B8%81%E6%96%B9%E6%B3%95
// [3] https://github.com/alexandred/VoodooI2C/blob/master/Documentation/GPIO%20Pinning.md
// [4] https://github.com/VoodooI2C/VoodooI2C/issues/392#issuecomment-706586493

DefinitionBlock ("", "SSDT", 2, "hack", "I2CX", 0x00000000)
{
    External (TPDM, FieldUnitObj)
    External (_SB_.PCI0.I2C0.TPL1, DeviceObj)
    
    Scope (\)
    {
        If (_OSI ("Darwin"))
        {
            TPDM = Zero
        }
    }


    Scope (_SB.PCI0.I2C0.TPL1)
    {
        If (_OSI ("Darwin"))
        {
            Name (TP7G, Buffer (0x10) // [4] force touchscreen to run in polling mode
            {
                /* 0000 */  0x82, 0xEB, 0x87, 0xEF, 0x00, 0x00, 0x00, 0x00,  // ........
                /* 0008 */  0x00, 0x00, 0x14, 0x87, 0x1A, 0xC6, 0xF8, 0x4B   // .......K
            })
        }
    }
}

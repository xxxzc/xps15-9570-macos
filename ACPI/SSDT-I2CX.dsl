// Enable GPIO mode for touchpad and touchscreen
// References:
// [1] https://github.com/xxxzc/xps15-9550-macos/issues/26#issuecomment-546838295
// [2] https://github.com/daliansky/OC-little/tree/master/19-I2C%E4%B8%93%E7%94%A8%E9%83%A8%E4%BB%B6
// [3] https://github.com/alexandred/VoodooI2C/blob/master/Documentation/GPIO%20Pinning.md
// [4] https://github.com/VoodooI2C/VoodooI2C/issues/392#issuecomment-810386204

DefinitionBlock ("", "SSDT", 2, "hack", "I2CX", 0x00000000)
{
    External (GPLI, FieldUnitObj)
    External (TPDM, FieldUnitObj)
    External (TPLM, FieldUnitObj)

    Scope (\)
    {
        If (_OSI ("Darwin"))
        {
            TPDM = Zero // enable GPIO mode for touchpad
            TPLM = Zero // enable GPIO mode for touchscreen
            GPLI = 0x1B // change touchscreen's GPIO pin to 0x1B [4]
        }
    }
}

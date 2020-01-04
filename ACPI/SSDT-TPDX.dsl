// Force I2C1.TPD0 use GPIO pining and disable I2C0
// References:
// [1] https://github.com/xxxzc/xps15-9550-macos/issues/26#issuecomment-546838295
// [2] https://github.com/daliansky/OC-little/tree/master/09-OCI2C-TPXX%E8%A1%A5%E4%B8%81%E6%96%B9%E6%B3%95
// [3] https://github.com/alexandred/VoodooI2C/blob/master/Documentation/GPIO%20Pinning.md

DefinitionBlock ("", "SSDT", 2, "hack", "TPDX", 0x00000000)
{
    External (SMD0, FieldUnitObj)
    External (USTP, FieldUnitObj)
    External (TPDM, FieldUnitObj) 

    Scope (\)
    {
        If (_OSI ("Darwin"))
        {
//            SMD0 = Zero // disable I2C0
            USTP = One // load SSCN and FMCN
            TPDM = Zero // enable GPIO pinning
        }
    }
}

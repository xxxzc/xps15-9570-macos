// Make brightness control work
// References:
// [1] https://github.com/daliansky/OC-little/blob/master/05-OC-PNLF%E6%B3%A8%E5%85%A5%E6%96%B9%E6%B3%95/%E5%AE%9A%E5%88%B6%E4%BA%AE%E5%BA%A6%E8%A1%A5%E4%B8%81/SSDT-PNLF-CFL.dsl
// [2] https://github.com/daliansky/OC-little/tree/master/%E4%BF%9D%E7%95%99%E9%A1%B9%E7%9B%AE/X02-%E4%BA%AE%E5%BA%A6%E5%BF%AB%E6%8D%B7%E9%94%AE%E8%A1%A5%E4%B8%81

DefinitionBlock ("", "SSDT", 2, "hack", "BCKM", 0x00000000)
{
    External (_SB_.ACOS, IntObj)
    External (_SB_.ACSE, IntObj)
    
    // inject PNLF for CoffeeLake to make brightness control work[1]
    Scope (_SB)
    {
        Device (PNLF)
        {
            Name (_ADR, Zero)
            Name (_HID, EisaId ("APP0002"))
            Name (_CID, "backlight")
            Name (_UID, 0x13)  // for CoffeeLake+
            
            Method (_STA, 0, NotSerialized)
            {
                If (_OSI ("Darwin")) { Return (0x0B) }
                Return (Zero)
            }
        }
    }
    
    // make BRT6 to be called on Darwin
    // in SMEE, EV5 is called only when OSID >= 0x20, and OSID:
    //     if ACOS == 0: init ACOS based on OS version
    //     return ACOS
    // hence set ACOS >= 0x20 can do the trick, and this trick affects less methods than _OSI renaming patch
    Scope (\)
    {
        If (_OSI ("Darwin"))
        {
            \_SB.ACOS = 0x80 // simulate Windows 2013(Win81)
            \_SB.ACSE = Zero // disable HIDD for faster power menu popup
        }
    }
}

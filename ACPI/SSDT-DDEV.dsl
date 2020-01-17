// Disable the following devices:
//  - Intel Power Engine (_SB_.PEPD)
// Patch: Rename PEPD._STA to XSTA
// Find: X1NUQQCgHpE=
// Replace: WFNUQQCgHpE=

DefinitionBlock ("", "SSDT", 2, "hack", "DGPU", 0x00000000)
{
    External (_SB_.PEPD, DeviceObj)
    External (_SB_.PEPD.XSTA, MethodObj)

    Scope (_SB_.PEPD)
    {
        Method (_STA, 0, NotSerialized)
        {
            If (_OSI ("Darwin"))
            {
                Return (Zero)
            }

            Return (XSTA ())
        }
    }
}


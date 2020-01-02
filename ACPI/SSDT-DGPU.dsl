// Disable discrete GPU on bootup
// Reference:
// [1] https://github.com/RehabMan/OS-X-Clover-Laptop-Config/blob/master/hotpatch/SSDT-DDGPU.dsl

DefinitionBlock ("", "SSDT", 2, "hack", "DGPU", 0x00000000)
{
    External (_SB_.PCI0.PEG0.PEGP._OFF, MethodObj)    // 0 Arguments

    // disable dGPU on bootup[1]
    Device (RMD1)
    {
        Name (_HID, "RMD10000")  // _HID: Hardware ID
        Method (_INI, 0, NotSerialized)  // _INI: Initialize
        {
            If ((_OSI ("Darwin")) && (CondRefOf (\_SB.PCI0.PEG0.PEGP._OFF)))
            {
                \_SB.PCI0.PEG0.PEGP._OFF ()
            }
        }
    }
}


// Disable discrete GPU
// Patch: Rename _WAK to ZWAK
// Find: 14 39 5F 57 41 4B 01
// Replace: 14 39 5A 57 41 4B 01
// Reference:
// [1] https://github.com/RehabMan/OS-X-Clover-Laptop-Config/blob/master/hotpatch/SSDT-DDGPU.dsl
// [2] https://github.com/RehabMan/OS-X-Clover-Laptop-Config/blob/master/hotpatch/SSDT-PTSWAK.dsl

DefinitionBlock ("", "SSDT", 2, "hack", "DGPU", 0x00000000)
{
    External (_SB_.PCI0.PEG0.PEGP._OFF, MethodObj)
    External (ZWAK, MethodObj)
    
    Method (DGPU, 0, NotSerialized)
    {
        If (_OSI ("Darwin") && CondRefOf(\_SB.PCI0.PEG0.PEGP._OFF)) { \_SB.PCI0.PEG0.PEGP._OFF() }
    }

    // disable dGPU on bootup[1]
    Device (RMD1)
    {
        Name (_HID, "RMD10000")
        Method (_INI, 0, NotSerialized)
        {
            DGPU ()
        }
        
        Method (_STA, 0, NotSerialized)
        {
            If (_OSI ("Darwin")) { Return (0x0F) }
            Return (Zero)
        }
    }

    // disable dGPU at wake[2]
    Method (_WAK, 1)
    {
        Local0 = ZWAK (Arg0)
        DGPU ()
        Return (Local0)
    }
}


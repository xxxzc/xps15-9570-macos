// Inject plugin-type=1 for XCPM
// Reference:
// [1] https://github.com/acidanthera/OpenCorePkg/blob/master/Docs/AcpiSamples/SSDT-PLUG.dsl

DefinitionBlock ("", "SSDT", 2, "ACDT", "CpuPlug", 0x00003000)
{
    External (_SB.PR00, ProcessorObj)

    Scope (_SB.PR00)
    {
        Method (_DSM, 4, NotSerialized)
        {
            If (LEqual (Arg2, Zero)) 
            {
               Return (Buffer (One) { 0x03 })
            }

            Return (Package (0x02)
            {
                "plugin-type", 
                One
            })
        }
    }
}

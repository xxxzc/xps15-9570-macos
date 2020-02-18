// Add various missing devices in PCI0
// Include EC, PMCR, DMAC, MCHC and SBUS
// #(Disabled)Rename ECDV to EC to not brake battery statistics for laptop[2]
// #(Disabled)Patch: Rename ECDV to EC
// Find: RUNEVg==	
// Replace: RUNfXw==
// References:
// [1] https://github.com/acidanthera/OpenCorePkg/blob/master/Docs/AcpiSamples/SSDT-SBUS-MCHC.dsl
// [2] https://www.insanelymac.com/forum/topic/338516-opencore-discussion/?do=findComment&comment=2685513
// [3] https://github.com/acidanthera/OpenCorePkg/blob/master/Docs/AcpiSamples/SSDT-EC.dsl
// [4] https://github.com/acidanthera/OpenCorePkg/blob/master/Docs/AcpiSamples/SSDT-PMC.dsl

DefinitionBlock ("", "SSDT", 2, "hack", "PCI0", 0x00000000)
{
    External (_SB_.PCI0, DeviceObj)
    External (_SB_.PCI0.LPCB, DeviceObj)
    External (_SB_.PCI0.SBUS.BUS0, DeviceObj)

    Scope (_SB.PCI0)
    {
        Device (MCHC) // MCHC[1]
        {
            Name (_ADR, Zero)  // _ADR: Address
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin")) 
                { Return (0x0F) }
                Return (Zero)
            }
        }
    }

    Scope (_SB.PCI0.LPCB)
    {
        // Add EC device to load AppleBusPowerController[3]
        Device (EC)
        {
            Name (_HID, "ACID0001")  // _HID: Hardware ID
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin")) 
                { Return (0x0F) }
                Return (Zero)
            }
        }
        
        // Intel 300-series PMC support [4]
        Device (PMCR)
        {
            Name (_HID, EisaId ("APP9876"))  // _HID: Hardware ID
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin")) 
                { Return (0x0F) }
                Return (Zero)
            }
            Name (_CRS, ResourceTemplate ()  // _CRS: Current Resource Settings
            {
                Memory32Fixed (ReadWrite,
                    0xFE000000,         // Address Base
                    0x00010000,         // Address Length
                    )
            })
        }
        
        Device (DMAC)
        {
            Name (_HID, EisaId ("PNP0200") /* PC-class DMA Controller */)  // _HID: Hardware ID
            Name (_CRS, ResourceTemplate ()  // _CRS: Current Resource Settings
            {
                IO (Decode16,
                    0x0000,             // Range Minimum
                    0x0000,             // Range Maximum
                    0x01,               // Alignment
                    0x20,               // Length
                    )
                IO (Decode16,
                    0x0081,             // Range Minimum
                    0x0081,             // Range Maximum
                    0x01,               // Alignment
                    0x11,               // Length
                    )
                IO (Decode16,
                    0x0093,             // Range Minimum
                    0x0093,             // Range Maximum
                    0x01,               // Alignment
                    0x0D,               // Length
                    )
                IO (Decode16,
                    0x00C0,             // Range Minimum
                    0x00C0,             // Range Maximum
                    0x01,               // Alignment
                    0x20,               // Length
                    )
                DMA (Compatibility, NotBusMaster, Transfer8_16, )
                    {4}
            })
            
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin")) 
                { Return (0x0F) }
                Return (Zero)
            }
        }
    }

    Device (_SB.PCI0.SBUS.BUS0) // SBUS[1]
    {
        Name (_CID, "smbus")  // _CID: Compatible ID
        Name (_ADR, Zero)  // _ADR: Address
        Device (DVL0)
        {
            Name (_ADR, 0x57)  // _ADR: Address
            Name (_CID, "diagsvault")  // _CID: Compatible ID
            Method (_DSM, 4, NotSerialized)  // _DSM: Device-Specific Method
            {
                If (!Arg2)
                {
                    Return (Buffer (One)
                    {
                         0x57                                             // W
                    })
                }

                Return (Package (0x02)
                {
                    "address", 
                    0x57
                })
            }
        }
        
        Method (_STA, 0, NotSerialized)  // _STA: Status
        {
            If (_OSI ("Darwin")) 
            { Return (0x0F) }
            Return (Zero)
        }
    }
}


// Type-C hotplug
// #(Disabled)Patch: Rename RP17.PXSX._RMV to XRMV
// Find: UlAxN1BYU1gUM19STVY=
// Replace: UlAxN1BYU1gUM1hSTVY=
// References:
// [1] https://www.insanelymac.com/forum/topic/324366-dell-xps-15-9560-4k-touch-1tb-ssd-32gb-ram-100-adobergb%E2%80%8B/
// [2] https://www.tonymacx86.com/threads/usb-c-hotplug-questions.211313/
// [3] https://github.com/the-darkvoid/XPS9360-macOS/issues/118
// [4] https://github.com/LuletterSoul/Dell-XPS-15-9570-macOS-Mojave/blob/master/EFI/CLOVER/ACPI/patched/SSDT-TB3-9570.aml

DefinitionBlock ("", "SSDT", 2, "hack", "TYPC", 0x00000000)
{
    External (_SB_.PCI0.RP17, DeviceObj)
    External (_SB_.PCI0.RP17.PXSX, DeviceObj)
    // External (_SB_.PCI0.RP17.PXSX.XRMV, MethodObj)
    External (_SB_.PCI0.RP17.UPSB, DeviceObj)

    Scope (\_SB.PCI0.RP17.PXSX)
    {
        Scope (PXSX)
        {
            /* key method to make type-c removable
            Method (_RMV, 0, NotSerialized)  // _RMV: Removal Status
            {
                If (_OSI ("Darwin"))
                {
                    Return (One)
                }
                Else
                {
                    Return (XRMV ())
                }
            }
            */
            
            Method (_STA, 0, NotSerialized)
            {
                If (_OSI ("Darwin")) 
                { Return (Zero) }
                Return (0x0F)
            }
            
            Method (NTFY, 2, NotSerialized)
            {
                If (LEqual (Arg0, 0x02))
                {
                    Notify (\_SB.PCI0.RP17.UPSB.DSB0.NHI0, 0x02)
                }
            }
        }
    }

    Scope (\_SB.PCI0.RP17)
    {
        Method (DTGP, 5, NotSerialized)
        {
            If ((Arg0 == ToUUID ("a0b5b7c6-1318-441c-b0c9-fe695eaf949b")))
            {
                If ((Arg1 == One))
                {
                    If ((Arg2 == Zero))
                    {
                        Arg4 = Buffer (One)
                        {
                             0x03                                             // .
                        }
                        Return (One)
                    }

                    If ((Arg2 == One))
                    {
                        Return (One)
                    }
                }
            }

            Arg4 = Buffer (One)
            {
                 0x00                                             // .
            }
            Return (Zero)
        }
        
        Device (UPSB)
        {
            Name (_ADR, Zero)  // _ADR: Address
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin")) 
                { Return (0x0F) }
                Return (Zero)
            }

            Device (DSB0)
            {
                Name (_ADR, Zero)  // _ADR: Address
                Method (_STA, 0, NotSerialized)  // _STA: Status
                {
                    Return (0x0F)
                }

                Device (NHI0)
                {
                    Name (_ADR, Zero)  // _ADR: Address
                    Name (_STR, Unicode ("Thunderbolt"))  // _STR: Description String
                    Method (_STA, 0, NotSerialized)  // _STA: Status
                    {
                        Return (0x0F)
                    }

                    Method (_DSM, 4, NotSerialized)  // _DSM: Device-Specific Method
                    {
                        If (LEqual (Arg0, ToUUID ("a0b5b7c6-1318-441c-b0c9-fe695eaf949b")))
                        {
                            Store (Package (0x0B)
                                {
                                    "AAPL,slot-name",
                                    Buffer (0x09)
                                    {
                                        "Built In"
                                    },

                                    "device_type",
                                    Buffer (0x19)
                                    {
                                        "Thunderbolt 3 Controller"
                                    },

                                    "model",
                                    Buffer (0x1E)
                                    {
                                        "GC Titan Ridge TB3 Controller"
                                    },

                                    "name",
                                    Buffer (0x0F)
                                    {
                                        "UPSB-DSB0-NHI0"
                                    },

                                    "power-save",
                                    One,
                                    Buffer (One)
                                    {
                                         0x00                                    
                                    }
                                }, Local0)
                            \_SB.PCI0.RP17.DTGP (Arg0, Arg1, Arg2, Arg3, RefOf (Local0))
                            Return (Local0)
                        }

                        Return (Zero)
                    }
                }

                Method (_DSM, 4, NotSerialized)  // _DSM: Device-Specific Method
                {
                    If (LEqual (Arg0, ToUUID ("a0b5b7c6-1318-441c-b0c9-fe695eaf949b")))
                    {
                        Store (Package (0x06)
                            {
                                "model",
                                Buffer (0x0A)
                                {
                                    "UPSB-DSB0"
                                },

                                "name",
                                Buffer (0x0A)
                                {
                                    "UPSB-DSB0"
                                },

                                "PCIHotplugCapable",
                                One
                            }, Local0)
                        \_SB.PCI0.RP17.DTGP (Arg0, Arg1, Arg2, Arg3, RefOf (Local0))
                        Return (Local0)
                    }

                    Return (Zero)
                }
            }

            Method (_DSM, 4, NotSerialized)  // _DSM: Device-Specific Method
            {
                If (LEqual (Arg0, ToUUID ("a0b5b7c6-1318-441c-b0c9-fe695eaf949b")))
                {
                    Store (Package (0x06)
                        {
                            "model",
                            Buffer (0x0A)
                            {
                                "UPSB"
                            },

                            "name",
                            Buffer (0x0A)
                            {
                                "UPSB"
                            },

                            "PCI-Thunderbolt",
                            One
                        }, Local0)
                    \_SB.PCI0.RP17.DTGP (Arg0, Arg1, Arg2, Arg3, RefOf (Local0))
                    Return (Local0)
                }

                Return (Zero)
            }
        }
    }
}


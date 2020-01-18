// USB power injection

DefinitionBlock ("", "SSDT", 2, "hack", "_USB", 0x00000000)
{
    External (_SB_.PCI0.LPCB, DeviceObj)
    
    Scope (\_SB)
    {
	    Device (USBX)
	    {
	        Name (_ADR, Zero)  // _ADR: Address
	        Method (_STA, 0, NotSerialized)  // _STA: Status
	        {
	            If (_OSI ("Darwin"))
	            {
	                Return (0x0F)
	            }
	            Else
	            {
	                Return (Zero)
	            }
	        }

	        Method (_DSM, 4, NotSerialized)  // _DSM: Device-Specific Method
	        {
	            If (!Arg2)
	            {
	                Return (Buffer (One)
	                {
	                     0x03                                             // .
	                })
	            }

	            Return (Package (0x04)
	            {
	                "kUSBSleepPortCurrentLimit", 
	                0x0BB8, 
	                "kUSBWakePortCurrentLimit", 
	                0x0BB8
	            })
	        }
	    }
    }
}
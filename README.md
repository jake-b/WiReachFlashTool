# WiReachFlashTool
A python script for talking to the ConnectOne iChip Boot-ROM over serial and applying a firmware update.

# License and Disclaimer

WiReach Flash Tool
Copyright (C) 2017 J. Bordens

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


**USE THIS SOFTWARE AT YOUR OWN RISK. Applying firmware updates to things
is a risky business, and this tool is not written or supported by the
hardware vendor.  Any error in the flash update process could cause
damage to your hardware module.  You may wind up with a bricked 
(non-functional) moudle with no way to recover.**

# How it works

There are four parts of the firmware update process of the ConnectOne 
iChip (used in the G2 WiReach modoules):

- Boot-ROM a very simple recovery tool which is stored in the ROM of 
the iChip.  You activate it on the serial interface by holding the MSEL
pin low for 5+ seconds during power up.

- The "FPro" - I think this means "flash programmer".  The Boot-ROM is
so simple that it does not know how to apply a flash update.  All it can
do is load a simple program.  The FPro is an binary image file that is
uploaded to the Boot-ROM and executed.  the FPro has the ability to 
perform the actual flash operation.  This FPro binary is not included
with this tool.  You can find the "Fpro.IMG" file as part of the 
[iChipConfig Utilty](http://www.connectone.com/?page_id=306)

- The Bootloader - used to hand hand off the boot process to the firmware
image.  It does not need to be updated, but is stored in Flash sector 0.
This tool does not support updating the bootloader because you need to
read the MAC address and serial number FIRST and re-apply it after an
update to the bootloader as this information is stored in this area of
memory.

- The firmware itself - stored in an "IMF" file.  An "IMZ" file is 
used for applying over-the-air, so you neeed the "IMF" for this tool.

# Instructions

To use this tool:

0. Install all Python pre-requisites.
1. Place Fpro.IMG in the same directory as the tool.
2. Run the tool with the -f parameter to select the flash type and the
-p parameter to select a serial port to use.  Include the IMF file
you wish to flash.  For example:

     python3 wireach_flash.py -f 4 -p /dev/tty.wchusbserial1420  i2128d811d29BCOM.imf

3. Cross your fingers and hope this doens't brick your module.
4. Be prepared to use the iChipConfig Utility mentioned earllier to 
fix (re-apply firwmare, bootloader) when this tool likely bricks your
module.

# References

[iChipConfig Utility](http://www.connectone.com/?page_id=306) is the
vendor-supported tool for Windows that performs these types of
firmware updates.  Also it can apply the bootloader which this tool
cannot.

[iChip Memory Structure and Troubleshooting](http://www.connectone.com/wp-content/uploads/2012/11/iChip-Memory-Structure-and-Troubleshooting.pdf) a document on how the
flash memory is configured and some troubeshooting steps you may need.

[iChip Programming Protocol](http://www.connectone.com/wp-content/uploads/2012/11/iChip-Flash-Programming-Protocol-1_20.pdf)
documentation on how to communicate with the Boot-ROM and Fpro to update
the firmware of the module.

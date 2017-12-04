#!/usr/bin/env python3

# WiReach Flash Tool v0.1
# Copyright (C) 2017 J. Bordens

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# BASICALLY -- USE THIS SOFTWARE AT YOUR OWN RISK.

# Dependencies
from ctypes import *
from pprint import pprint
from enum import IntEnum
import os, sys
import argparse
import serial
import time
from tqdm import tqdm

# Send a command to the given serial interface
def sendCommand(ser, cmd):
    print(cmd)
    cmd += "\r"
    ser.write(cmd.encode('ascii'))
    ser.flush()

# Wait for a character for a given amount of time.
def WaitForCharacter(ser, character, timeout=1):
    timeout = time.time() + timeout
    ser.timeout = 0.1
    while time.time() < timeout:
        ch = ser.read(1)
        if (ch == character.encode('ascii')):
            return True
    return False

# Send the command to erase a specific list of sectors
def FLEraseSectors(ser, lngFirstSector, lngLastSector):
    cmd = "E " + str(lngFirstSector)
    for i in range(lngFirstSector+1, lngLastSector+1):
        cmd += "," + str(i)
    sendCommand(ser, cmd)

# Write a buffer to an address on the device
def FLWriteBuffer(ser, data, lngAddress):
    cmd = "D " + format(lngAddress, 'x') + "," + format(len(data)//2, 'x') + ":"
    #print(cmd)
    ser.write(cmd.encode('ascii'))
    ser.write(data) #do not use sendCommand fn because no \r
    ser.flush()
    WaitForCharacter(ser, ">", timeout=1)

# Break an image file into smaller sections and write to the device
def FLWriteImage(ser, lngAddress, lngFileLen, file):
    lngFileLenInWords = lngFileLen // 2 if lngFileLen % 2 == 0 else (lngFileLen // 2) + 1
    #print(lngFileLenInWords)
    lngWholeK = lngFileLenInWords // 1024
    lngPartial = lngFileLenInWords % 1024
    totalBytes = 0;
    pbar = tqdm(total=lngFileLen, unit="bytes")
    for i in range(0, lngWholeK):
        #print(hex(lngAddress) + f": Sending block {i+1} of {lngWholeK}")
        data = file.read(2048)
        FLWriteBuffer(ser, data, lngAddress)
        lngAddress += 2048
        totalBytes += 2048
        pbar.update(2048)
    if lngPartial > 0:
        #print(hex(lngAddress) + f": Sending partial block {lngPartial} bytes")
        data = file.read(lngPartial*2)
        FLWriteBuffer(ser, data, lngAddress)
        lngAddress += lngPartial*2
        totalBytes += lngPartial*2
        pbar.update(lngPartial*2)
    pbar.close()

# Enumaration of flash types
class FlashType(IntEnum):
    SPI_TYPE_A = 1
    EBI_TYPE_A = 2 #1Mb
    EBI_TYPE_B = 3 #8Mb
    EBI_TYPE_C = 4 #2Mb

# Struct for parsing the header of the firmware file.
class IMG_HDR(Structure):
    _fields_ = [
    	("lmagic", c_int),
    	("lformat_ver", c_int),
    	("strSwVer",  c_char * 8),
    	("strManuLogo", c_char * 32),
    	("strLinkDate", c_char * 12),
    	("iSwType1", c_short),
    	("iSwType2", c_short),
    	("lSerialNumRest_l", c_int),
    	("lSerialNumRest_h", c_int),
    	("lImgSize", c_int),
    	("lRamImgSize", c_int),
    	("lpEntryPoint", c_int),
    	("iCompressType", c_short),
    	("iEncryption", c_short * 2),
    	("lFlshImgSize", c_int),
    	("lReserved", c_int * 3),
    	("iCSum", c_short),
    	("iStartFlag", c_short * 2),
    	("iNofBlks", c_short),
    	("iFill", c_short)]

    def getdict(self):
        return dict((field, getattr(self, field)) for field, _ in self._fields_)

# Parse the command line
parser = argparse.ArgumentParser(description="WiReach Boot-ROM Flash Tool")
parser.add_argument("-f", "--flashtype", type=int, help="1=SPI Flash; 2=1Mbyte; 3=8Mbyte; 4=2Mbyte", required=True)
parser.add_argument("-p", "--port", help="path to serial device")
parser.add_argument('firmware_file', help="path to .imf firmware file")
args = parser.parse_args()

# Initialize the serial port
ser = serial.Serial()
if args.port != None:
    ser.port = args.port
    ser.baudrate = 115200
    ser.open()
    print("Opened serial port: ", ser.name)

# Get the file length of the firmware file (used later for progress)
lngFileLen = os.stat(args.firmware_file).st_size
print("Firmware image file length: ", lngFileLen)
with open(args.firmware_file, 'rb') as file:
    img_hdr = IMG_HDR()

    if args.flashtype == FlashType.SPI_TYPE_A:
        print("WARNING: SPI_TYPE_A (1) unsupported and likely does not work.")
        file.seek(49)

    #read the header
    file.readinto(img_hdr)
    
    #seek back to the start of the image file
    file.seek(0)

    lngAppAddress = 0
    blnIsBBImage = False
    if args.flashtype == FlashType.SPI_TYPE_A:
        lngAppAddress = 0x30000000
    else:
        lngAppAddress = img_hdr.lpEntryPoint & 0xFFFFF000
        if (img_hdr.iSwType2 & 0x8000):
            print("WARNING: BBImage type is unsupported and likely does not work.")
            blnIsBBImage = True
            file.seek(0x101)
            lngFileLen -= 0x100

    # Print the calculated entrypoint
    print("EntryPoint Address = ", hex(lngAppAddress))

    if blnIsBBImage:
        # Note, this is where you'd FLGet2128MacAndSerial and store it for later use
        # SInce we don't support that in this dinky little utility, just exit with error
        print("ERROR: This tool is incomplete, BBImage is unsupported.")
        sys.exit(1)

    # Determine what needs to be erased based on FLASH type
    lngFirstSectorToErase = 0
    lngLastSectorToErase = 0
    if args.flashtype == FlashType.SPI_TYPE_A:
        lngFirstSectorToErase = 0
        lngLastSectorToErase = 1
    elif args.flashtype == FlashType.EBI_TYPE_A:
        lngFirstSectorToErase = 4
        lngLastSectorToErase = 11
    elif args.flashtype == FlashType.EBI_TYPE_C:
        lngFirstSectorToErase = 4
        lngLastSectorToErase = 16
    elif args.flashtype == FlashType.EBI_TYPE_B:
        print("ERROR: EBI_TYPE_B (8Mb is reserved and not supported)")
        sys.exit(1)
    else:
        print("ERROR: Unknown flash type")
        sys.exit(1)

    # Connect to Boot-ROM
    print("Connecting to Boot-ROM...")
    ser.write(b"U")
    if not WaitForCharacter(ser, ">", timeout=5):
        print("ERROR: Did not get prompt back in time (Boot-ROM)")
        exit(1)

    # Put Boot-ROM into Load mode
    ser.write(b"L")
    if not WaitForCharacter(ser, ">", timeout=5):
        print("ERROR: Did not get prompt back in time (Boot-ROM)")
        exit(1)

    with open("Fpro.IMF", 'rb') as imf_file:
        data = imf_file.read(16)
        if len(data) != 16:
            print("Error: unable to read first 16 bytes of FPro.IMF file")
            exit(1)

        #write first 16 bytes
        print("Writing FPro header (first 16 bytes)")
        ser.write(data)

        #wait for prompt
        if not WaitForCharacter(ser, ">", timeout=5):
            print("ERROR: Did not get prompt back in time (FPro first 16)")
            exit(1)

        print(f"Writing FPro data.")

        fpro_bytes = 16
        fpro_total = os.stat("Fpro.IMF").st_size
        with tqdm(total=fpro_total, unit="bytes") as pbar:
            while True:
                chunk = imf_file.read(512)
                if chunk:
                    fpro_bytes += len(chunk)
                    ser.write(chunk)
                    ser.flush()
                    pbar.update(len(chunk))
                else:
                    break
        print(f"Finished writing FPro: {fpro_bytes} bytes")

        if not WaitForCharacter(ser, ">", timeout=15):
            print("ERROR: Did not get prompt back in time (Full FPro)")
            #exit(1)

        # Close IMF done
        imf_file.close()

    # Set baud back to 9600
    ser.baudrate=9600

    # Wait 5 seconds per spec
    print("Sleeping for 5 seconds")
    time.sleep(5)

    # Connect to FPro
    print("Connecting to FPro...")
    sendCommand(ser, "U")
    if not WaitForCharacter(ser, ">", timeout=5):
        print("ERROR: Did not get prompt back in time (FPro)")
        exit(1)

    print("Setting flash type...")
    cmd = "F " + str(args.flashtype) #the spec seems to indicate no space, but we use one
    sendCommand(ser, cmd)
    if not WaitForCharacter(ser, ">", timeout=5):
        print("ERROR: Did not get prompt back in time (set flash type)")
        exit(1)

    print("Increasing baud rate...")
    cmd = "B 115200" #space is important according to spec
    sendCommand(ser, cmd)

    # Check for the prompt in the old baud rate, as per the spec.
    # I have found this doens't always work.
    if not WaitForCharacter(ser, ">", timeout=5):
        print("ERROR: Did not get prompt back in time (set baud)")

    ser.baudrate = 115200 # set new baud rate.

    # Extra check for the prompt at the new baud rate.
    ser.write(b'\r')
    if not WaitForCharacter(ser, ">", timeout=5):
        print("ERROR: Did not get prompt back in time (set baud)")
        exit(1)
    
    # Erase the sectors relevant for the flash type selected
    print(f"Erasing sectors {lngFirstSectorToErase} - {lngLastSectorToErase}")
    FLEraseSectors(ser, lngFirstSectorToErase, lngLastSectorToErase)

    # Set serial timeout for erase operation
    # one second for each sector, per the sepc
    ser.timeout = (1+lngLastSectorToErase-lngFirstSectorToErase)
    print(f"Waiting for erase operation {ser.timeout} seconds.")
    while True:
        ch = ser.read(1)
        # per spec, if you get a # back, then send a \r
        if (ch == b"#"):
            print("RECEIVED: #")
            ser.write(b'\r')
        elif (ch == b">"):
            print("Erase operation complete")
            break
        elif (ch == b""):
            print("Timeout while waiting for erase operation.")
            exit(1)

    # Write the image
    FLWriteImage(ser, lngAppAddress, lngFileLen, file)

    if not WaitForCharacter(ser, ">", timeout=5):
        print("ERROR: Did not get prompt back in time (post-write)")
        exit(1)

    # Start the new firmware after successfully writing the image
    print("Staring new firmware...")
    sendCommand(ser, "S")

import sys
import time
from serial.tools import list_ports
from serial import Serial, PARITY_NONE, SerialException


# Using a USB to RS485 converter
# Hex ID represented as strings
USB_VENDOR_ID = "1A86"
USB_PRODUCT_ID = "7523"

# Note: 1 register = 1 WORD (16bits or 2 bytes)
SIZE_REGISTERS = 1
STARTING_ADDRESS = 3000
LAST_ADDRESS = 4000
SLAVE_ID = 0x01
FUNCTION_CODE = 0x04


def get_usb_port() -> str:
    for device in sorted(list_ports.comports()):
        if device.vid and device.pid:
            # Compare as Hex represented as strings
            if USB_VENDOR_ID == format(device.vid, 'X') and USB_PRODUCT_ID == format(device.pid, 'X'):
                # Name of the COM port
                return device.name
    return None


def calculate_crc(message_without_crc: bytes) -> bytes:
    crc = 0xFFFF

    for byte in message_without_crc:
        crc ^= byte
        for i in range(8, 0, -1):
            if (crc & 0x0001) != 0:
                crc >>=1
                crc ^= 0xA001
            else:
                crc >>= 1
    
    byte_swap = ((crc << 8) & 0xff00) | ((crc >> 8) & 0x00ff)

    # Note sometimes python truncates byte array for display purposes - all bytes are still there
    return byte_swap.to_bytes(2, 'big')


def form_modbus_request(slaveId: int, functionCode: int, i: int, sizeRegisters: int) -> bytes:
    slave_id = slaveId.to_bytes(1, 'big')
    function_code = functionCode.to_bytes(1, 'big')
    address = i.to_bytes(2, 'big')
    size_registers = sizeRegisters.to_bytes(2, 'big')

    message_before_crc = slave_id + function_code + address + size_registers
    crc = calculate_crc(message_before_crc)

    if crc:
        return message_before_crc + crc
    else:
        return None
    

def poll_modbus(port: str):
    try:
        with Serial(port=port, baudrate=9600, stopbits=1, parity=PARITY_NONE, timeout=2) as ser:
            for i in range(STARTING_ADDRESS, LAST_ADDRESS + 1):
                # ser.reset_input_buffer()
                # ser.reset_output_buffer()
                modbus_request = form_modbus_request(SLAVE_ID, FUNCTION_CODE, i, SIZE_REGISTERS)

                if modbus_request:
                    print("Request: " + modbus_request.hex(' '))
                else:
                    continue

                ser.write(modbus_request)
                time.sleep(0.2)
                modbus_response = ser.read_until(size=ser.in_waiting)

                if modbus_response:
                    print("Response: " + modbus_response.hex(' '))

            ser.close()

    except SerialException:
        print("Failed to open serial port.")
    except Exception as exception:
        print(exception)


if __name__ == '__main__':
    port = get_usb_port()

    if port is None:
        print("No USB found")
        sys.exit()
    else:
        poll_modbus(port)

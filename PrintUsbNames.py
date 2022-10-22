from serial.tools.list_ports import comports

if __name__ == '__main__':
    ports = comports()
    for port_info in ports:
        print(f'{port_info.name} : {port_info.description}')
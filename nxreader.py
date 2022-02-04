"""Simplified class to read information from sys-botbase
   https://github.com/Lincoln-LM/PyNXReader"""
import socket
import binascii
from time import sleep

class NXReader:
    """Simplified class to read information from sys-botbase"""
    def __init__(self, ip_address = None, port = 6000):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(1)
        self.socket.connect((ip_address, port))
        print('Connected')
        self.ls_lastx = 0
        self.ls_lasty = 0
        self.rs_lastx = 0
        self.rs_lasty = 0
        self._configure()

    def _configure(self):
        self.send_command('configure echoCommands 0')

    def send_command(self,content):
        """Send a command to sys-botbase on the switch"""
        content += '\r\n' #important for the parser on the switch side
        self.socket.sendall(content.encode())

    def recv(self,size):
        """Receive response from sys-botbase"""
        return binascii.unhexlify(self.socket.recv(2 * size + 1)[0:-1])

    def close(self):
        """Close connection to switch"""
        print("Exiting...")
        self.pause(0.5)
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()
        print('Disconnected')

    # A/B/X/Y/LSTICK/RSTICK/L/R/ZL/ZR/PLUS/MINUS/DLEFT/DUP/DDOWN/DRIGHT/HOME/CAPTURE
    def click(self,button):
        """Press and release button"""
        self.send_command('click '+ button)

    def press(self,button):
        """Press and hold button"""
        self.send_command('press '+ button)

    def release(self,button):
        """Release held button"""
        self.send_command('release '+ button)

    # setStick LEFT/RIGHT <xVal from -0x8000 to 0x7FFF> <yVal from -0x8000 to 0x7FFF
    def move_stick(self,stick,x_val,y_val):
        """Move stick to position"""
        self.send_command(f"setStick {stick} {hex(x_val)} {hex(y_val)}")

    def move_left_stick(self,x_val = None, y_val = None):
        """Move the left stick to position"""
        if x_val is not None:
            self.ls_lastx = x_val
        if y_val is not None:
            self.ls_lasty = y_val
        self.move_stick('LEFT',self.ls_lastx,self.ls_lasty)

    def move_right_stick(self,x_val = None, y_val = None):
        """Move the right stick to position"""
        if x_val is not None:
            self.rs_lastx = x_val
        if y_val is not None:
            self.rs_lasty = y_val
        self.move_stick('RIGHT',self.rs_lastx,self.rs_lasty)

    #peek <address in hex, prefaced by 0x> <amount of bytes, dec or hex with 0x>
    #poke <address in hex, prefaced by 0x> <data, if in hex prefaced with 0x>
    def read(self,address,size,filename = None):
        """Read bytes from heap"""
        self.send_command(f'peek 0x{address:X} 0x{size:X}')
        sleep(size/0x8000)
        buf = self.recv(size)
        if filename is not None:
            if filename == '':
                filename = f'dump_heap_0x{address:X}_0x{size:X}.bin'
            with open(filename,'wb') as file_out:
                file_out.write(buf)
        return buf

    def read_int(self,address,size,filename = None):
        """Read integer from heap"""
        return int.from_bytes(self.read(address,size,filename),'little')

    def write(self,address,data):
        """Write data to heap"""
        self.send_command(f'poke 0x{address:X} 0x{data}')

    def read_main(self,address,size,filename = None):
        """Read bytes from main"""
        self.send_command(f'peekMain 0x{address:X} 0x{size:X}')
        sleep(size/0x8000)
        buf = self.recv(size)
        if filename is not None:
            if filename == '':
                filename = f'dump_heap_0x{address:X}_0x{size:X}.bin'
            with open(filename,'wb') as file_out:
                file_out.write(buf)
        return buf

    def read_main_int(self,address,size,filename = None):
        """Read integer from main"""
        return int.from_bytes(self.read_main(address,size,filename),'little')

    def write_main(self,address,data):
        """Write data to main"""
        self.send_command(f'pokeMain 0x{address:X} 0x{data}')

    def read_pointer(self,pointer,size,filename = None):
        """Read bytes from pointer"""
        jumps = pointer.replace("[","").replace("main","").split("]")
        command = f'pointerPeek 0x{size:X} 0x{" 0x".join(jump.replace("+","") for jump in jumps)}'
        self.send_command(command)
        sleep(size/0x8000)
        buf = self.recv(size)
        if filename is not None:
            if filename == '':
                filename = f'dump_heap_{pointer}_0x{size:X}.bin'
            with open(filename,'wb') as file_out:
                file_out.write(buf)
        return buf

    def read_pointer_int(self,pointer,size,filename = None):
        """Read integer from pointer"""
        return int.from_bytes(self.read_pointer(pointer,size,filename = filename),'little')

    def write_pointer(self,pointer,data):
        """Write data to pointer"""
        jumps = pointer.replace("[","").replace("main","").split("]")
        command = f'pointerPoke 0x{data} 0x{" 0x".join(jump.replace("+","") for jump in jumps)}'
        self.send_command(command)

    @staticmethod
    def pause(duration):
        """Pause connection to switch"""
        sleep(duration)

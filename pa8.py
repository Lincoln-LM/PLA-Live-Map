"""PLA Pokemon Format"""
class ByteStruct:
    """Object to represent a structure of bytes"""
    def __init__(self,buf):
        self.data = bytearray(buf[:])

    def get_ulong(self,offset):
        """Pull u64 from bytes"""
        return int.from_bytes(self.data[offset:offset + 8], byteorder='little') 

    def get_uint(self,offset):
        """Pull u32 from bytes"""
        return int.from_bytes(self.data[offset:offset + 4], byteorder='little')

    def get_ushort(self,offset):
        """Pull u16 from bytes"""
        return int.from_bytes(self.data[offset:offset + 2], byteorder='little')

    def get_byte(self,offset):
        """Pull u8 from bytes"""
        return self.data[offset]

class Pa8(ByteStruct):
    """PLA Pokemon Format"""
    # pylint: disable=too-many-public-methods
    # pkxs contain a lot of information that may need to be accessed
    STOREDSIZE = 360
    BLOCKSIZE = 88

    def __init__(self,buf):
        ByteStruct.__init__(self,buf)
        if self.is_encrypted:
            self.decrypt()

    @property
    def encryption_constant(self):
        """Pokemon's EC"""
        return self.get_uint(0x0)

    @property
    def checksum(self):
        """Pokemon's checksum"""
        return self.get_ushort(0x6)

    @property
    def species(self):
        """Pokemon's species"""
        return self.get_ushort(0x8)

    @property
    def sidtid(self):
        """Pokemon's sidtid"""
        return self.get_uint(0x0C)

    @property
    def ability(self):
        """Pokemon's ability index"""
        return self.get_ushort(0x14)

    @property
    def ability_num(self):
        """Pokemon's species-specific ability index"""
        return self.get_byte(0x16) & 0x7

    @property
    def ability_string(self):
        """Pokemon's species-specific ability string"""
        return self.ability_num if self.ability_num < 4 else 'H'

    @property
    def pid(self):
        """Pokemon's PID"""
        return self.get_uint(0x1C)

    @property
    def nature(self):
        """Pokemon's nature"""
        return self.get_byte(0x20)

    @property
    def gender(self):
        """Pokemon's gender"""
        return (self.get_byte(0x22) >> 2) & 0x3

    @property
    def form_index(self):
        """Pokemon's form index"""
        return self.get_ushort(0x24)

    @property
    def evs(self):
        """Pokemon's EVs"""
        return [self.data[0x26],
                self.data[0x27],
                self.data[0x28],
                self.data[0x2A],
                self.data[0x2B],
                self.data[0x29]]

    @property
    def move1(self):
        """Pokemon's first move"""
        return self.get_ushort(0x54)

    @property
    def move2(self):
        """Pokemon's second move"""
        return self.get_ushort(0x56)

    @property
    def move3(self):
        """Pokemon's third move"""
        return self.get_ushort(0x58)

    @property
    def move4(self):
        """Pokemon's fourth move"""
        return self.get_ushort(0x5A)

    @property
    def iv32(self):
        """Pokemon's ivs as a u32"""
        return self.get_uint(0x94)

    @property
    def ivs(self):
        """Pokemon's ivs"""
        iv32 = self.iv32
        return [iv32 & 0x1F,
                (iv32 >> 5) & 0x1F,
                (iv32 >> 10) & 0x1F,
                (iv32 >> 20) & 0x1F,
                (iv32 >> 25) & 0x1F,
                (iv32 >> 15) & 0x1F]

    def calc_checksum(self):
        """Calculate the pokemons checksum for data validation"""
        chk = 0
        for i in range(8,Pa8.STOREDSIZE,2):
            chk += self.get_ushort(i)
            chk &= 0xFFFF
        return chk

    @property
    def shiny_type(self):
        """Shiny type of a pokemon"""
        xor = (self.sidtid >> 16) ^ (self.sidtid & 0xFFFF) ^ (self.pid >> 16) ^ (self.pid & 0xFFFF)
        if xor > 15:
            return 0
        return 2 if xor == 0 else 1

    @property
    def shiny_string(self):
        """Shiny type of a pokemon as a string"""
        return 'None' if self.shiny_type == 0 else 'Star' if self.shiny_type == 1 else 'Square'

    @property
    def is_valid(self):
        """Check the validity of a pokemon"""
        return self.checksum == self.calc_checksum() and not self.is_encrypted

    @property
    def is_encrypted(self):
        """Check if the pokemon is encrypted"""
        return self.get_ushort(0x70) != 0 and self.get_ushort(0xC0) != 0

    def decrypt(self):
        """Decrypt an ea8"""
        seed = self.encryption_constant
        shuffle_order = (seed >> 13) & 0x1F

        self.__crypt_pkm__(seed)
        self.__shuffle__(shuffle_order)

    def __crypt_pkm__(self,seed):
        """Run __crypt__ specific to the pokemon size"""
        self.__crypt__(seed, 8, Pa8.STOREDSIZE)

    def __crypt__(self, seed, start, end):
        """Encrypt/decrypt a based on seed"""
        i = start
        while i < end:
            seed = seed * 0x41C64E6D + 0x6073
            self.data[i] ^= (seed >> 16) & 0xFF
            i += 1
            self.data[i] ^= (seed >> 24) & 0xFF
            i += 1

    def __shuffle__(self, shuffle_order):
        """Shuffle the bytes"""
        idx = 4 * shuffle_order
        sdata = bytearray(self.data[:])
        for block in range(4):
            ofs = Pa8.BLOCKPOSITION[idx + block]
            self.data[8 + Pa8.BLOCKSIZE * block : 8 + Pa8.BLOCKSIZE * (block + 1)] \
              = sdata[8 + Pa8.BLOCKSIZE * ofs : 8 + Pa8.BLOCKSIZE * (ofs + 1)]

    BLOCKPOSITION = [
        0, 1, 2, 3,
        0, 1, 3, 2,
        0, 2, 1, 3,
        0, 3, 1, 2,
        0, 2, 3, 1,
        0, 3, 2, 1,
        1, 0, 2, 3,
        1, 0, 3, 2,
        2, 0, 1, 3,
        3, 0, 1, 2,
        2, 0, 3, 1,
        3, 0, 2, 1,
        1, 2, 0, 3,
        1, 3, 0, 2,
        2, 1, 0, 3,
        3, 1, 0, 2,
        2, 3, 0, 1,
        3, 2, 0, 1,
        1, 2, 3, 0,
        1, 3, 2, 0,
        2, 1, 3, 0,
        3, 1, 2, 0,
        2, 3, 1, 0,
        3, 2, 1, 0,

        # duplicates of 0-7 to eliminate modulus
        0, 1, 2, 3,
        0, 1, 3, 2,
        0, 2, 1, 3,
        0, 3, 1, 2,
        0, 2, 3, 1,
        0, 3, 2, 1,
        1, 0, 2, 3,
        1, 0, 3, 2,
    ]

"""Xoroshiro Random Number Generator"""
class XOROSHIRO:
    """Xoroshiro Random Number Generator"""
    ulongmask = 2 ** 64 - 1
    uintmask = 2 ** 32 - 1

    def __init__(self, seed0, seed1 = 0x82A2B175229D6A5B):
        self.seed = [seed0, seed1]

    def reseed(self, seed0, seed1 = 0x82A2B175229D6A5B):
        """Reseed rng without creating a new object"""
        self.seed = [seed0, seed1]

    @property
    def state(self):
        """Return the full state of the rng as read from memory"""
        seed0, seed1 = self.seed
        return seed0 | (seed1 << 64)

    @staticmethod
    def rotl(number, k):
        """Rotate number left by k"""
        return ((number << k) | (number >> (64 - k))) & XOROSHIRO.ulongmask

    def next(self):
        """Generate the next random number and advance the rng"""
        seed0, seed1 = self.seed
        result = (seed0 + seed1) & XOROSHIRO.ulongmask
        seed1 ^= seed0
        self.seed = [XOROSHIRO.rotl(seed0, 24) ^ seed1 ^ ((seed1 << 16) & XOROSHIRO.ulongmask),
                     XOROSHIRO.rotl(seed1, 37)]
        return result

    def previous(self):
        """Generate the previous random number and advance the rng backwards"""
        seed0, seed1 = self.seed
        seed1 = XOROSHIRO.rotl(seed1, 27)
        seed0 = (seed0 ^ seed1 ^ (seed1 << 16)) & XOROSHIRO.ulongmask
        seed0 = XOROSHIRO.rotl(seed0, 40)
        seed1 ^= seed0
        self.seed = [seed0,seed1]
        return (seed0 + seed1) & XOROSHIRO.ulongmask

    def nextuint(self):
        """Generate the next random number as a uint"""
        return self.next() & XOROSHIRO.uintmask

    @staticmethod
    def get_mask(maximum):
        """Get the bit mask for rand(maximum)"""
        maximum -= 1
        for i in range(6):
            maximum |= maximum >> (1 << i)
        return maximum

    def rand(self, maximum = uintmask):
        """Generate a random number in the range of [0,maximum)"""
        mask = XOROSHIRO.get_mask(maximum)
        res = self.next() & mask
        while res >= maximum:
            res = self.next() & mask
        return res

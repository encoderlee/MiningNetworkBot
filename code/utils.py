from binascii import hexlify


def str_to_hex(c):
    hex_data = hexlify(bytearray(c, 'ascii')).decode()
    return int(hex_data, 16)

def char_subtraction(a, b, add):
    x = str_to_hex(a)
    y = str_to_hex(b)
    ans = str((x - y) + add)
    if len(ans) % 2 == 1:
        ans = '0' + ans
    return int(ans)

def char_to_symbol(c):
    if 'a' <= c <= 'z':
        return char_subtraction(c, 'a', 6)
    if '1' <= c <= '5':
        return char_subtraction(c, '1', 1)
    return 0

def string_to_name(s):
    i = 0
    name = 0
    while i < len(s):
        name += (char_to_symbol(s[i]) & 0x1F) << (64 - 5 * (i + 1))
        i += 1
    if i > 12:
        name |= char_to_symbol(s[11]) & 0x0F
    return name

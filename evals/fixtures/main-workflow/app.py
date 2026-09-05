import sys


def greeting(name: str) -> str:
    return f"Hello, {name}!"


if __name__ == "__main__":
    print(greeting(sys.argv[1]))

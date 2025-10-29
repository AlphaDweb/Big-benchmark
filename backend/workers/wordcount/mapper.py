import sys

for line in sys.stdin:
    for word in line.strip().split():
        if word:
            print(f"{word}\t1")



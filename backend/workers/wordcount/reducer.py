import sys

current = None
count = 0

for line in sys.stdin:
    try:
        word, num = line.strip().split("\t", 1)
        n = int(num)
    except Exception:
        continue
    if current is None:
        current = word
        count = n
    elif word == current:
        count += n
    else:
        print(f"{current}\t{count}")
        current = word
        count = n

if current is not None:
    print(f"{current}\t{count}")



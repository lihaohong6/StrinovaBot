import hashlib

original = "引航者，这里是欧泊搜查官米雪儿，再次幸会！"
hashed = "B29A67CA46E1183F8A88619A6870C128"


def run_xxhash(s: str, seed: int | None = None, encoding=None) -> str:
    import xxhash

    if seed is None:
        result = xxhash.xxh128(s)
    else:
        result = xxhash.xxh128(s, seed)
    return result.hexdigest()


def run_md5(s: str, encoding: str = "utf-8") -> str:
    return hashlib.md5(s.encode(encoding)).hexdigest()


def run_murmur(s: str, encoding: str = "utf-8") -> str:
    import mmh3
    hasher = mmh3.mmh3_x86_128()
    hasher.update(s.encode(encoding))
    return hasher.digest().hex()


algorithms = [run_md5, run_murmur, run_xxhash]

for algo in algorithms:
    for encoding in ["utf-8", "gb2312", "gbk"]:
        r = algo(original, encoding=encoding)
        r = r.upper()
        assert len(r) == len(hashed)
        if r == hashed:
            print("\n".join(["====" * 10]))
        print(r)

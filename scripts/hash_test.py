import hashlib

originals = ["星绘",
             "引航者，这里是欧泊搜查官米雪儿，再次幸会！",
             "对于我们搜查官来说，市民朋友的事就是我们自己家的事。"
             ]
hashed_list = ["7B9C7C0A431371F8F9509DB0BC445E96",
               "B29A67CA46E1183F8A88619A6870C128",
               "653A74A64751681AC9D88C9040344A59"]


def run_xxhash(s: str, seed: int | None = None, encoding=None) -> str:
    import xxhash

    if seed is None:
        result = xxhash.xxh128(s)
    else:
        result = xxhash.xxh128(s, seed)
    return result.hexdigest()


def run_md5(s: str, encoding: str = "utf-8") -> str:
    return hashlib.md5(s.encode(encoding)).hexdigest()


def double_md5(s: str, encoding: str = "utf-8") -> str:
    return run_md5(run_md5(s))


def triple_md5(s: str, encoding: str = "utf-8") -> str:
    return double_md5(run_md5(s))


def run_murmur(s: str, encoding: str = "utf-8") -> str:
    import mmh3
    hasher = mmh3.mmh3_x86_128()
    hasher.update(s.encode(encoding))
    return hasher.digest().hex()


def main():
    algorithms = [run_md5, double_md5, triple_md5, run_murmur, run_xxhash]

    for i in range(len(originals)):
        original = originals[i]
        hashed = hashed_list[i]
        for algo in algorithms:
            for encoding in ["utf-8", "gb2312"]:
                r = algo(original, encoding=encoding)
                r = r.upper()
                assert len(r) == len(hashed)
                if r == hashed:
                    print("\n".join(["====" * 10]))
                # print(r)


main()

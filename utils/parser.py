import re


def parse_fm(raw: str):

    m = re.match(
        r"^---\n([\s\S]*?)\n---",
        raw
    )

    if not m:
        return {}

    obj = {}

    for line in m.group(1).split("\n"):

        if ": " not in line:
            continue

        k, *v = line.split(": ")

        val = ": ".join(v).strip().strip('"')

        if k == "tags":
            val = re.findall(
                r'"([^"]+)"',
                ": ".join(v)
            )

        obj[k.strip()] = val

    return obj
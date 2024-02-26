import argparse


def tokenize(text):
    return text.split("<script")


def only_with_type(tokens):
    output = [tokens[0]]

    for token in tokens[1:]:
        parts = token.split(">")
        head = parts[0]
        tail = ">".join(parts[1:])

        tail_parts = tail.split("</script>")
        script = tail_parts[0]
        remainder = "</script>".join(tail_parts[1:])

        if 'type="' in head.replace(" ", ""):
            output.append("<script" + head + ">" + script + "</script>")

        output.append(remainder)

    return output


def reconstruct(tokens):
    return "".join(tokens)


def main(args):
    file = open(args.file, 'r')
    text = file.read()
    tokens = tokenize(text)
    tokens = only_with_type(tokens)
    text = reconstruct(tokens)

    print(text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Removes corrupt script tags from HTML documents')
    parser.add_argument('--file', help='the path to a file to sanitize')
    args = parser.parse_args()
    main(args)

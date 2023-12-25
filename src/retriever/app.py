from argparse import ArgumentParser

from .retriever import Retriever


def parse_args():
    parser = ArgumentParser(
        prog="Retriever",
        description="Script para ejecutar el retriever. El retriever recibe"
        " , como mínimo, el fichero donde se guarda el índice invertido.",
    )

    parser.add_argument(
        "-i",
        "--index-file",
        type=str,
        help="Ruta del fichero con el índice invertido",
        required=True,
    )

    parser.add_argument(
        "-q", "--query", type=str, help="Query a resolver", required=False
    )

    parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="Ruta al fichero de texto con una query por línea",
        required=False,
    )

    # Añade aquí cualquier otro argumento que condicione
    # el funcionamiento del retriever

    args = parser.parse_args()
    if not args.query and not args.file:
        parser.error(
            "Debes introducir una query (-q) o un fichero (-f) con queries."
        )
    if args.query and args.file:
        parser.error(
            "Introduce solo una query (-q) o un fichero (-f), no ambos."
        )
    return args


if __name__ == "__main__":
    args = parse_args()
    retriever = Retriever(args)
    if args.query:
        retriever.search_query(args.query)
    elif args.file:
        retriever.search_from_file(args.file)

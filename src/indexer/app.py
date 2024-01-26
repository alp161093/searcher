from argparse import ArgumentParser

from .indexer import Indexer


def parse_args():
    parser = ArgumentParser(
        prog="Indexer",
        description="Script para ejecutar el indexer. El indexer recibe,"
        " como mínimo, la carpeta donde se han almacenado los"
        " resultados del crawler y la carpeta donde se almacenará"
        " el índice invertido",
    )

    parser.add_argument(
        "-i",
        "--input-folder",
        type=str,
        default="etc/webpages",
        help="Carpeta que contiene los ficheros con el contenido de las URL",
        required=False,
    )

    parser.add_argument(
        "-o",
        "--output-name",
        type=str,
        help="Fichero destino donde almacenar el índice",
        required=True,
    )

    # Añade aquí cualquier otro argumento que condicione
    # el funcionamiento del indexer
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    indexer = Indexer(args)
    indexer.build_index()

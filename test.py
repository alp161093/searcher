from src.crawler.crawler import Crawler
from src.retriever.retriever import Retriever
from argparse import ArgumentParser

def parse_args_crawler():
    parser = ArgumentParser(
        prog="Crawler",
        description="Script para ejecutar el crawler. El crawler recibe una"
        " URL y un número máximo de webs e irá almacenando los"
        " resultados en disco",
    )

    parser.add_argument(
        "-u",
        "--url",
        type=str,
        default="https://universidadeuropea.com",
        help="URL base desde donde empezar a crawlear.",
    )

    parser.add_argument(
        "-m",
        "--max_webs",
        type=int,
        default=300,
        help="Número máximo de webs a crawlear.",
    )

    parser.add_argument(
        "-o",
        "--output-folder",
        type=str,
        default="etc/webpages",
        help="Carpeta destino donde almacenar el contenido"
        " de las URLs crawleadas.",
    )
    return parser.parse_args()

def parse_args_retriever():
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
    #llamada crawler
    """args = parse_args_crawler()
    crawler = Crawler(args)
    crawler.crawl()"""

    args = parse_args_retriever()
    retriever = Retriever(args)
    if args.query:
        retriever.search_query(args.query)
    elif args.file:
        retriever.search_from_file(args.file)
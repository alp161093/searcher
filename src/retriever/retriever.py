import pickle as pkl
import re
import sys
import unicodedata
from argparse import Namespace
from copy import deepcopy
from dataclasses import dataclass
from time import time
from typing import Dict, List

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import TreebankWordTokenizer

from ..indexer.indexer import Index


@dataclass
class Result:
    """Clase que contendrá un resultado de búsqueda"""

    url: str
    snippet: str

    def __str__(self) -> str:
        return f"{self.url} -> {self.snippet}"


class Retriever:
    """Clase que representa un recuperador"""

    def __init__(self, args: Namespace):
        self.args = args
        self.index = self.load_index()

    def search_query(self, query: str) -> List[Result]:
        """Método para resolver una query.
        Este método debe ser capaz, al menos, de resolver consultas como:
        "grado AND NOT master OR docencia", con un procesado de izquierda
        a derecha. Por simplicidad, podéis asumir que los operadores AND,
        NOT y OR siempre estarán en mayúsculas.

        Ejemplo para "grado AND NOT master OR docencia":

        posting["grado"] = [1,2,3] (doc ids que tienen "grado")
        NOT posting["master"] = [3, 4, 5] (doc ids que no tienen "master")
        posting["docencia"] = [6] (doc ids que tienen docencia)

        [1, 2, 3] AND [3, 4, 5] OR [6] = [3] OR [6] = [3, 6]

        Args:
            query (str): consulta a resolver
        Returns:
            List[Result]: lista de resultados que cumplen la consulta
        """
        listado_results = []
        query_sinAcentos = self.remove_acentos(query)  # se quitan los acentos
        results = self.resolve_query(query_sinAcentos)
        # ordenamos
        results_notas = self.score(results, query_sinAcentos)
        for result in results_notas:
            # coger url del documento
            document = next(
                (doc for doc in self.index.documents if doc.id == result), None
            )
            # trabajamos para quedarnos con las primeras 20 palabras del texto
            texto = document.text
            palabras = texto.split()
            resumen = " ".join(palabras[:20])
            item = Result(url=document.url, snippet=resumen)
            listado_results.append(item)
        self.mostrarResultados(
            query, listado_results
        )  # se muestran todos los resultados por la pantalla
        return listado_results

    def remove_acentos(self, texto: str):
        texto_normalizado = unicodedata.normalize("NFD", texto)
        texto_sin_acentos = "".join(
            c for c in texto_normalizado if not unicodedata.combining(c)
        )

        return texto_sin_acentos

    def resolve_query(self, query: str) -> List[int]:
        #'"GRADO DE INFORMATICA" AND ( MASTER AND TEST ) OR NOT DOCTORADO'
        resultados = []
        query_tokenizada = self.shuntingYard(
            query
        )  # ['GRADO DE INFORMATICA', 'MASTER', 'TEST', 'AND', 'AND', 'DOCTORADO', 'NOT', 'OR']
        resultados = self.resolver_query(query_tokenizada)
        return resultados

    def tokenize(self, query: str):
        tokens = re.findall(
            r'("[^"]+"|\bAND\b|\bOR\b|\bNOT\b|\(|\)|\w+)', query
        )
        resultado = []
        for token in tokens:
            if token.startswith('"') and token.endswith('"'):
                token_procesado = token[1:-1]
            else:
                token_procesado = token
            resultado.append(token_procesado)
        return resultado

    def prec(self, c: str) -> int:
        # Sirve para darle la precedencia a cada operador, cuanto mayor es el resultado menor precedencia tiene
        if c == "NOT":
            return 1

        if c == "AND":
            return 2

        if c == "OR":
            return 3

        return sys.maxsize  # Devolvemos un 4 si es un parentesis

    def isOperando(self, c: str) -> bool:
        return not c in ["AND", "OR", "NOT", "(", ")"]

    def shuntingYard(self, query: str):
        tokens = self.tokenize(query)
        if not tokens:
            return ""

        listado_aux = []
        resultado = []
        # ['GRADO DE INFORMATICA', 'AND','(','MASTER','AND','TEST',')','OR','NOT','DOCTORADO']
        for c in tokens:
            if c == "(":
                listado_aux.append(c)
            elif c == ")":
                while listado_aux and listado_aux[-1] != "(":
                    resultado.append(listado_aux.pop())
                listado_aux.pop()
            elif self.isOperando(c):
                resultado.append(c)
            else:
                while (
                    listado_aux
                    and listado_aux[-1] != "("
                    and self.prec(c) >= self.prec(listado_aux[-1])
                ):
                    resultado.append(listado_aux.pop())
                listado_aux.append(c)

        while listado_aux:
            resultado.append(listado_aux.pop())

        return resultado  # ['GRADO DE INFORMATICA', 'MASTER', 'TEST', 'AND', 'AND', 'DOCTORADO', 'NOT', 'OR']

    def calculaNOT(self, posting_a, operador):
        if operador == "NOT":
            return self._not_(posting_a)

    def calcula(self, posting_a, posting_b, operador):
        if operador == "AND":
            return self._and_(posting_a, posting_b)
        if operador == "OR":
            return self._or_(posting_a, posting_b)

    def resolver_query(self, query: str) -> List[int]:
        listado_aux = []
        for token in query:
            if " " in token:
                posting_token = self.resolve_posicionales(token)
                listado_aux.append(posting_token)
            else:
                if self.isOperando(token):
                    posting_token = self.index.postings[token]
                    listado_aux.append(posting_token)
                elif token == "NOT":
                    token_1 = listado_aux.pop()
                    listado_aux.append(self.calculaNOT(token_1, token))
                else:
                    token_1 = listado_aux.pop()
                    token_2 = listado_aux.pop()
                    listado_aux.append(self.calcula(token_1, token_2, token))

        return listado_aux.pop()

    def resolve_posicionales(self, query: str) -> Dict[int, List[int]]:
        # pasamos a minuscula la query
        query = query.lower()
        # tokenizamos la query para trabajar con ella más comodamente
        tokenizer = TreebankWordTokenizer()
        listadoQuery = tokenizer.tokenize(query)
        # quitamos stopWords porque en las postings no tenemos stopwords y si en la query hay alguna stopWord no devolveriamos nada
        listado_Sin_StopWords = self.remove_stopwords(listadoQuery)
        # posting de la pimera palabra de la query, la vamos a almacenar porque vamos a trabajar con ella
        posting_primera_palabra = self.index.postings[listado_Sin_StopWords[0]]
        # contadores con los que vamos a trabajar
        tamaño = len(listado_Sin_StopWords)
        contador_restar = 1
        continuar = True
        # resultados donde vaya coincidiendo las posiciones
        resultados = {}
        aux = {}
        while contador_restar < tamaño and continuar == True:
            if len(resultados) == 0:
                for documento in posting_primera_palabra:
                    numero_posicion_buscar = tamaño - contador_restar
                    if (
                        documento
                        in self.index.postings[
                            listado_Sin_StopWords[numero_posicion_buscar]
                        ]
                    ):
                        for posicion in posting_primera_palabra[documento]:
                            posicion_buscar = posicion + numero_posicion_buscar
                            if (
                                posicion_buscar
                                in self.index.postings[
                                    listado_Sin_StopWords[
                                        numero_posicion_buscar
                                    ]
                                ][documento]
                            ):
                                if documento not in resultados:
                                    resultados[documento] = [posicion]
                                else:
                                    resultados[documento].append(posicion)
            else:
                # aqui ya trabajamos sobre resultados, porque es donde hemos ido filtrando las palabras anteriores
                for documento in aux:
                    numero_posicion_buscar = tamaño - contador_restar
                    if (
                        documento
                        in self.index.postings[
                            listado_Sin_StopWords[numero_posicion_buscar]
                        ]
                    ):
                        for posicion in aux[documento]:
                            posicion_buscar = posicion + numero_posicion_buscar
                            if (
                                posicion_buscar
                                not in self.index.postings[
                                    listado_Sin_StopWords[
                                        numero_posicion_buscar
                                    ]
                                ][documento]
                            ):
                                # como este documento de la palabra que estamos buscando no esta quitamos esa posicion del listado de posiciones de ese documento
                                resultados[documento].remove(posicion)
                                if len(resultados[documento]) == 0:
                                    del resultados[documento]

                    else:
                        # la palabra que estamos buscando no tiene ese documento en la posting por lo tanto lo tenemos que quitarlo del listado de resultado
                        del resultados[documento]

            contador_restar += 1
            # se hace deepcopy porque si le damos simplemente el valor del uno al otro al eliminar datos en uno se nos eliminan en ambos
            aux = deepcopy(resultados)
            if len(resultados) == 0:
                continuar = False
        return resultados

    def remove_stopwords(self, words: List[str]) -> List[str]:
        """Método para eliminar stopwords después del tokenizado.
        Puedes usar cualquier lista de stopwords, e.g., de NLTK.

        Args:
            words (List[str]): lista de palabras de un documento
        Returns:
            List[str]: lista de palabras del documento, sin stopwords
        """
        nltk.download("stopwords")
        listadoStopWords = stopwords.words("spanish")
        listadoAux = []
        for word in words:
            if word not in listadoStopWords:
                listadoAux.append(word)
        return listadoAux

    def search_from_file(self, fname: str) -> Dict[str, List[Result]]:
        """Método para hacer consultas desde fichero.
        Debe ser un fichero de texto con una consulta por línea.

        Args:
            fname (str): ruta del fichero con consultas
        Return:
            Dict[str, List[Result]]: diccionario con resultados de cada consulta
        """
        with open(fname, "r", encoding="utf-8") as fr:
            ts = time()
            n_queries = 0
            results = {}
            for query in fr:
                query_resuelta = self.search_query(query)
                results[query] = query_resuelta
                n_queries += 1
            te = time()
            print(f"Time to solve {n_queries}: {te-ts}")
            return results

    def load_index(self) -> Index:
        """Método para cargar un índice invertido desde disco."""
        with open(self.args.index_file, "rb") as fr:
            return pkl.load(fr)

    def _and_(self, posting_a: List[int], posting_b: List[int]) -> List[int]:
        """Método para calcular la intersección de dos posting lists.
        Será necesario para resolver queries que incluyan "A AND B"
        en `search_query`.

        Args:
            posting_a (List[int]): una posting list
            posting_b (List[int]): otra posting list
        Returns:
            List[int]: posting list de la intersección
        """
        posting_response = []
        for indice_doc in posting_a:
            if indice_doc in posting_b:
                posting_response.append(indice_doc)
        return posting_response

    def _or_(
        self, posting_a: Dict[int, List[int]], posting_b: Dict[int, List[int]]
    ) -> Dict[int, List[int]]:
        """Método para calcular la unión de dos posting lists.
        Será necesario para resolver queries que incluyan "A OR B"
        en `search_query`.

        Args:
            posting_a (List[int]): una posting list
            posting_b (List[int]): otra posting list
        Returns:
            List[int]: posting list de la unión
        """
        posting_response = deepcopy(posting_a)
        for b in posting_b:
            if b not in posting_response:
                posting_response[b] = posting_b[b]
        return dict(sorted(posting_response.items()))

    def _not_(self, posting_a: List[int]) -> List[int]:
        """Método para calcular el complementario de una posting list.
        Será necesario para resolver queries que incluyan "NOT A"
        en `search_query`

        Args:
            posting_a (List[int]): una posting list
        Returns:
            List[int]: complementario de la posting list
        """

        """listado auxiliar donde vamos a meter los documentos que no estan en la posting list que hemos pasado como parametro de entrada"""
        documentosResponse = []
        for doc in self.index.documents:
            if doc.id not in posting_a:
                """si no esta dentro de la posting list lo guardamos"""
                documentosResponse.append(doc.id)
        return documentosResponse

    def score(self, resultados: List[int], query: str) -> Dict[int, int]:
        query = self.shuntingYard(query)
        documentos_notas = {}
        notas_aux = []
        for doc in resultados:
            for token in query:
                if " " in token:
                    notas_aux.append(10)
                else:
                    if self.isOperando(token):
                        if doc in self.index.postings[token]:
                            nota = len(self.index.postings[token][doc])
                            if nota > 10:
                                nota = 10
                        else:
                            nota = 0
                        notas_aux.append(nota)
                    elif token == "NOT":
                        notas_aux.pop()
                        notas_aux.append(10)
                    else:
                        token_1 = notas_aux.pop()
                        token_2 = notas_aux.pop()
                        notas_aux.append(
                            self.calculaScore(token_1, token_2, token)
                        )
            documentos_notas[doc] = notas_aux.pop()
        return dict(
            sorted(
                documentos_notas.items(), key=lambda item: item[1], reverse=True
            )
        )

    def calculaScore(self, nota_a, nota_b, operador):
        if operador == "AND":
            return (nota_a + nota_b) / 2
        if operador == "OR":
            nota_total = nota_a + nota_b
            if nota_total >= 10:
                return 10
            else:
                return nota_total

    def mostrarResultados(self, query: str, listado_results: List[Result]):
        print("Query -> " + query)
        print("Resultados ordenados por nota descendente->")
        for result in listado_results:
            print("URL: " + result.url)
            print("Snippet: " + result.snippet)
            print()

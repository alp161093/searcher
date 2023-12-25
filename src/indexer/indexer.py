import pickle as pkl
from argparse import Namespace
from dataclasses import dataclass, field
import string
from time import time
from typing import Dict, List
import os
import json
from bs4 import BeautifulSoup
import nltk
from nltk.tokenize import TreebankWordTokenizer
from nltk.corpus import stopwords
import requests
from io import BytesIO
from PyPDF2 import PdfReader


@dataclass
class Document:
    """Dataclass para representar un documento.
    Cada documento contendrá:
        - id: identificador único de documento.
        - title: título del documento.
        - url: URL del documento.
        - text: texto del documento, parseado y limpio.
    """

    id: int
    title: str
    url: str
    text: str


@dataclass
class Index:
    """Dataclass para representar un índice invertido.

    - "postings": diccionario que mapea palabras a listas de índices. E.g.,
                  si la palabra w1 aparece en los documentos con índices
                  d1, d2 y d3, su posting list será [d1, d2, d3].

    - "documents": lista de `Document`.
    """

    postings: Dict[str, List[int]] = field(default_factory=lambda: {})
    documents: List[Document] = field(default_factory=lambda: [])

    def save(self, output_name: str) -> None:
        """Serializa el índice (`self`) en formato binario usando Pickle"""
        with open(output_name, "wb") as fw:
            pkl.dump(self, fw)


@dataclass
class Stats:
    """Dataclass para representar estadísticas del indexador"""

    n_words: int = field(default_factory=lambda: 0)
    n_docs: int = field(default_factory=lambda: 0)
    building_time: float = field(default_factory=lambda: 0.0)

    def __str__(self) -> str:
        return (
            f"Words: {self.n_words}\n"
            f"Docs: {self.n_docs}\n"
            f"Time: {self.building_time}"
        )


class Indexer:
    """Clase que representa un indexador"""

    def __init__(self, args: Namespace):
        self.args = args
        self.index = Index()
        self.stats = Stats()

    def build_index(self) -> None:
        """Método para construir un índice.
        El método debe iterar sobre los ficheros .json creados por el crawler.
        Para cada fichero, debe crear y añadir un nuevo `Document` a la lista
        `documents`, al que se le asigna un id entero secuencial, su título
        (se puede extraer de <title>), su URL y el texto del documento
        (contenido parseado y limpio). Al mismo tiempo, debe ir actualizando
        las posting lists. Esto es, dado un documento, tras parsearlo,
        limpiarlo y tokenizarlo, se añadirá el id del documento a la posting
        list de cada palabra en dicho documento. Al final, almacenará el objeto
        Index en disco como un fichero binario.

        [Nota] El indexador no debe distinguir entre mayúsculas y minúsculas, por
        lo que deberás convertir todo el texto a minúsculas desde el principio.
        """
        idSecuencial = 1
        # Indexing
        ts = time()
        """Se obtiene la lista de archivos de la carpeta que esta predefinida en la practica"""
        archivos_en_carpeta = os.listdir(self.args.input_folder)
        """Filtrar los archivos que tienen la extensión .json"""
        archivos_json = [archivo for archivo in archivos_en_carpeta if archivo.endswith('.json')]

        """Se recorren todos los archivos que se han crawleado"""
        for archivo_json in archivos_json:
            ruta_completa = os.path.join(self.args.input_folder, archivo_json)
            """Se lee el archivo y lo pasamos a la variable datos_json para poder trabajar con el"""
            with open(ruta_completa, 'r') as archivo:
                datos_json = json.load(archivo)
            
            textoPdf = self.extract_text_from_pdf(datos_json['url'])
            """obtengo el titulo del fichero de la etiqueta title dentro del head de la web"""
            parser = BeautifulSoup( datos_json['text'], "html.parser")
            titulo = parser.find(name = "title").text
            """Nos quedamos con el lo que se encuentra dentro del div de clase page, que es de donde tenemos que sacar el texto de las etiquetas y se lo pasamos a la funcion parse para trabajar con el"""
            """"textoEtiquetaDiv = parser.find(name = "div", class_ = "page")"""
            textoParse = self.parse(datos_json['text'])
            """remove_split_symbols"""
            textoParse = self.remove_split_symbols(textoParse)
            """remove_punctuation""" 
            textoParse = self.remove_punctuation(textoParse)
            """remove_elongated_spaces"""
            textoParse = self.remove_elongated_spaces(textoParse)
            """tokenize"""
            listaPalabras = self.tokenize(textoParse)
            """remove_stopwords"""
            listaPalabrasSinStopWords = self.remove_stopwords(listaPalabras)

            """se crea un documento nuevo con los datos correspondientes y se almacena en el listado de documentos de index"""
            doc = Document(idSecuencial, titulo,  datos_json['url'], textoParse)
            self.index.documents.append(doc)
            idSecuencial += 1

            for word in listaPalabrasSinStopWords:
                if word not in self.index.postings:
                    self.index.postings[word] = [doc.id]
                else:
                    self.index.postings[word].append(doc.id)
                

        te = time()

        # Save index
        self.index.save(self.args.output_name)

        # Show stats
        self.show_stats(building_time=te - ts)

    def extract_text_from_pdf(self, url: str) -> str:
        response = requests.get(url)
        pdf_content = BytesIO(response.content)
        reader = PdfReader(pdf_content)
        number_of_pages = len(reader.pages)
        response = ""
        indice  = 0
        while indice < number_of_pages:
            page = reader.pages[indice]
            text = page.extract_text()
            response += text + " "
            indice += 1 
        return text

    def parse(self, text: str) -> str:
        """Método para extraer el texto de un documento.
        Puedes utilizar la librería 'beautifulsoup' para extraer solo
        el texto del bloque principal de una página web (lee el pdf de la
        actividad para más detalles)

        Args:
            text (str): texto de un documento
        Returns:
            str: texto parseado
        """
        """Array de las etiquetas que tenemos que parsear"""
        etiquetasAParsear =  ['h1', 'h2', 'h3', 'b', 'i', 'p', 'a']
        """response es variable donde se almacenara todo el texo"""
        response = ""
        parser = BeautifulSoup(text, "html.parser")
        """se saca todo lo que hay dentro de la etiqueta div con clase page"""
        textoEtiquetaDiv = parser.find(name = "div", class_ = "page")

        for etiqueta in etiquetasAParsear:
            textoEtiquetas = textoEtiquetaDiv.find_all(name=etiqueta)
            for txt in textoEtiquetas:
                response += txt.text + " "

        
        """etiquetasH1 = textoEtiquetaDiv.find_all(name="h1")
        for H1 in etiquetasH1:
            response += H1.text + " "

        etiquetasH2 = parser.find_all(name="h2")
        for H2 in etiquetasH2:
            response += H2.text + " "

        etiquetasH3 = parser.find_all(name="h3")
        for H3 in etiquetasH3:
            response += H3.text + " "

        etiquetasB = parser.find_all(name="b")
        for B in etiquetasB:
            response += B.text + " "

        etiquetasI = parser.find_all(name="i")
        for I in etiquetasI:
            response += I.text + " "

        etiquetasP = parser.find_all(name="p")
        for P in etiquetasP:
            response += P.text + " "

        etiquetasA = parser.find_all(name="a")
        for A in etiquetasA:
            response += A.text + " """

        return response.lower()

    def tokenize(self, text: str) -> List[str]:
        """Método para tokenizar un texto. Esto es, convertir
        un texto a una lista de palabras. Puedes utilizar tokenizers
        existentes en NLTK, Spacy, etc. O simplemente separar por
        espacios en blanco.

        Args:
            text (str): text de un documento
        Returns:
            List[str]: lista de palabras del documento
        """
        tokenizer = TreebankWordTokenizer()
        return tokenizer.tokenize(text)

    def remove_stopwords(self, words: List[str]) -> List[str]:
        """Método para eliminar stopwords después del tokenizado.
        Puedes usar cualquier lista de stopwords, e.g., de NLTK.

        Args:
            words (List[str]): lista de palabras de un documento
        Returns:
            List[str]: lista de palabras del documento, sin stopwords
        """
        nltk.download('stopwords')
        listadoStopWords = stopwords.words('spanish')
        listadoAux = []
        for word in words:
            if(word not in listadoStopWords and word not in listadoAux):
                listadoAux.append(word)
        return listadoAux           

    def remove_punctuation(self, text: str) -> str:
        """Método para eliminar signos de puntuación de un texto:
         < > ¿ ? , ; : . ( ) [ ] " ' ¡ !

        Args:
            text (str): texto de un documento
        Returns:
            str: texto del documento sin signos de puntuación.
        """
        puntuacion = string.punctuation
        puntuacion += '¿¡'
        # Crea una tabla de traducción para eliminar los símbolos de puntuación
        tabla_de_traduccion = str.maketrans("", "", puntuacion)
        
        # Aplica la tabla de traducción al texto
        texto_sin_puntuacion = text.translate(tabla_de_traduccion)
    
        return texto_sin_puntuacion

    def remove_elongated_spaces(self, text: str) -> str:
        """Método para eliminar espacios duplicados.
        E.g., "La     Universidad    Europea" --> "La Universidad Europea"

        Args:
            text (str): texto de un documento
        Returns:
            str: texto sin espacios duplicados
        """
        return " ".join(text.split())

    def remove_split_symbols(self, text: str) -> str:
        """Método para eliminar símbolos separadores como
        saltos de línea, retornos de carro y tabuladores.

        Args:
            text (str): texto de un documento
        Returns:
            str: texto sin símbolos separadores
        """
        return text.replace("\n", " ").replace("\t", " ").replace("\r", " ")

    def show_stats(self, building_time: float) -> None:
        self.stats.building_time = building_time
        self.stats.n_words = len(self.index.postings)
        self.stats.n_docs = len(self.index.documents)
        print(self.stats)

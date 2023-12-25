from argparse import Namespace
import json
import os
from queue import Queue
from typing import Set
from bs4 import BeautifulSoup
import requests


class Crawler:
    """Clase que representa un Crawler"""

    def __init__(self, args: Namespace):
        self.args = args

    def crawl(self) -> None:
        """Método para crawlear la URL base. `crawl` debe crawlear, desde
        la URL base `args.url`, usando la librería `requests` de Python,
        el número máximo de webs especificado en `args.max_webs`.
        Puedes usar una cola para esto:

        https://docs.python.org/3/library/queue.html#queue.Queue

        Para cada nueva URL que se visite, debe almacenar en el directorio
        `args.output_folder` un fichero .json con, al menos, lo siguiente:

        - "url": URL de la web
        - "text": Contenido completo (en crudo, sin parsear) de la web
        """
        countJSON = 0
        listaAuxUrls = []
        queue = Queue()
        queue.put(self.args.url)
        while  queue.not_empty and len(listaAuxUrls) < self.args.max_webs: 
            url = queue.get()
            if url not in listaAuxUrls:
                listaAuxUrls.append(url)
            """obtenemos el texto de la pagina"""
            response = requests.get(url)
            """Creamos el json en la ruta especificada"""
            oJson = {"url": url, "text" : response.text}
            rutaDestino = self.args.output_folder
            path = os.path.join(rutaDestino, str(countJSON) + ".json")
            with open(path, 'w') as archivo:
                json.dump(oJson, archivo)
            """se incrementa el contador de JSON para que no coincidan con el nombre"""
            countJSON += 1
            """buscamos todas las urls dentro del texto de la url"""
            urls = self.find_urls(response.text)
            """recorremos todas las urls que nos han llegado y antes de meterlas en la cola hay que ver """
            for url in urls:
                """si no esta en la lista auxiliar significa que es la primera vez que se pasa por ella, si está significa que ya la hemos leido anteriormente"""
                if (url not in listaAuxUrls) and len(listaAuxUrls) < self.args.max_webs:
                    queue.put(url)
                    listaAuxUrls.append(url)
                else:
                    print("URL: " + url + "--- YA ESTA EN EL LISTADO")
        print("se ha llegado al tope queue: " + str(queue.qsize()) + " listaAux: " + str(len(listaAuxUrls))) 
        
        while queue.not_empty:
            url =queue.get() 
            if url == "https://universidadeuropea.com/resources/media/documents/GRUPO-PEE_Politica-de-Cumplimiento-2023-ESP.pdf":
                    print()
            """Creamos el json en la ruta especificada"""
            oJson = {"url": url, "text" : response.text}
            rutaDestino = self.args.output_folder
            path = os.path.join(rutaDestino, str(countJSON) + ".json")
            with open(path, 'w') as archivo:
                json.dump(oJson, archivo)
            """se incrementa el contador de JSON para que no coincidan con el nombre"""
            countJSON += 1


    def find_urls(self, text: str) -> Set[str]:
        """Método para encontrar URLs de la Universidad Europea en el
        texto de una web. SOLO se deben extraer URLs que aparezcan en
        como valores "href" y que sean de la Universidad, esto es,
        deben empezar por "https://universidadeuropea.com".
        `find_urls` será útil para el proceso de crawling en el método `crawl`

        Args:
            text (str): text de una web
        Returns:
            Set[str]: conjunto de urls (únicas) extraídas de la web
        """
        parser = BeautifulSoup(text, "html.parser")
        urls = parser.find_all(name = "a", attrs={"href" : True})
        urlsCasteadas = []
        for url in urls:
            enlace = url['href']
            if(enlace.startswith("https://universidadeuropea.com")):
                urlsCasteadas.append(enlace)
        return urlsCasteadas



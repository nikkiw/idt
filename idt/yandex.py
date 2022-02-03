import json
import os

import requests
from bs4 import BeautifulSoup as bs4
from fake_headers import Headers
from rich.progress import Progress

from idt.utils.download_images import download
from idt.utils.remove_corrupt import erase_duplicates

__name__ = "yandex"


class Size:
    def __init__(self):
        self.large = 'large'
        self.medium = 'medium'
        self.small = 'small'


class Preview:
    def __init__(self, url: str,
                 width: int,
                 height: int):
        self.url = url
        self.width = width
        self.height = height
        self.size = str(width) + '*' + str(height)


class Result:
    def __init__(self, title: (str, None),
                 description: (str, None),
                 domain: str,
                 url: str,
                 width: int,
                 height: int,
                 preview: Preview):
        self.title = title
        self.description = description
        self.domain = domain
        self.url = url
        self.width = width
        self.height = height
        self.size = str(width) + '*' + str(height)
        self.preview = preview


class YandexSearchEngine:
    def __init__(self, data, n_images, folder, resize_method, root_folder, size):
        self.sizeYandex = Size()
        self.headers = Headers(headers=True).generate()

        self.data = data
        self.n_images = n_images
        self.folder = folder
        self.resize_method = resize_method
        self.root_folder = root_folder
        self.size = size
        self.downloaded_images = 0
        self.search()

    def get_result(self, query: str, sizes: Size) -> list:
        request = requests.get('https://yandex.ru/images/search',
                               params={"text": query,
                                       "nomisspell": 1,
                                       "noreask": 1,
                                       "isize": sizes
                                       },
                               headers=self.headers)

        soup = bs4(request.text, 'html.parser')
        items_place = soup.find('div', {"class": "serp-list"})
        output = list()
        try:
            items = items_place.find_all("div", {"class": "serp-item"})
        except AttributeError:
            return output

        for item in items:
            data = json.loads(item.get("data-bem"))
            image = data['serp-item']['img_href']
            image_width = data['serp-item']['preview'][0]['w']
            image_height = data['serp-item']['preview'][0]['h']

            snippet = data['serp-item']['snippet']
            try:
                title = snippet['title']
            except KeyError:
                title = None
            try:
                description = snippet['text']
            except KeyError:
                description = None
            domain = snippet['domain']

            preview = 'https:' + data['serp-item']['thumb']['url']
            preview_width = data['serp-item']['thumb']['size']['width']
            preview_height = data['serp-item']['thumb']['size']['height']

            output.append(Result(title, description, domain, image,
                                 image_width, image_height,
                                 Preview(preview, preview_width, preview_height)))

        return output

    def search(self):

        images = self.get_result(self.data, self.sizeYandex.large)
        len_result = max(len(images), self.n_images)

        if not os.path.exists(self.root_folder):
            os.mkdir(self.root_folder)

        target_folder = os.path.join(self.root_folder, self.folder)
        if not os.path.exists(target_folder):
            os.mkdir(target_folder)

        with Progress() as progress:
            task1 = progress.add_task("[blue]Downloading {x} class...".format(x=self.data), total=len_result)
            for item in images[:len_result]:
                try:
                    download(item.url, self.size, self.root_folder, self.folder, self.resize_method)
                    self.downloaded_images += 1
                    progress.update(task1, advance=1)
                except Exception as e:
                    continue

                self.downloaded_images -= erase_duplicates(target_folder)

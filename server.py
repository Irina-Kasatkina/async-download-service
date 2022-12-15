# coding=utf-8

"""Asynchronous microservice for downloading files"""

import argparse
import asyncio
import logging
import os

import aiofiles
from aiohttp import web


CHUNK_SIZE = 102400
PHOTOS_FOLDER = 'test_photos'


def create_parser():
    """Create command line parameter parser."""

    parser = argparse.ArgumentParser(description='Асинхронный микросервис для загрузки файлов.')
    parser.add_argument('-l', '--logging', action='store_true', help='включить логирование')
    parser.add_argument('-d', '--delay', action='store_true', help='включить задержку ответа')
    parser.add_argument(
        '-p',
        '--path',
        default=os.path.join(os.getcwd(), PHOTOS_FOLDER),
        help='путь к каталогу с фотографиями'
    )
    return parser


async def archive(request):
    """Archive requested folder and send zip to user."""

    archive_hash = request.match_info.get('archive_hash', '')
    archive_path = os.path.join(request.app.args.path, archive_hash)
    if not archive_hash or not os.path.exists(archive_path):
        raise web.HTTPNotFound(text='Архив не существует или был удален')

    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/html'
    response.headers['Content-Disposition'] = f'attachment; filename="wedding.zip"'
    await response.prepare(request)

    args = ['-qr', '-', '.']
    process = await asyncio.create_subprocess_exec(
        'zip',
        *args,
        cwd=archive_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    try:
        while not process.stdout.at_eof():
            zip_chunk = await process.stdout.read(CHUNK_SIZE)
            if request.app.args.logging:
                logging.debug('Sending archive chunk ...')
            await response.write(zip_chunk)
            if request.app.args.delay:
                await asyncio.sleep(1)
    except asyncio.CancelledError:
        if request.app.args.logging:
            logging.debug('Download was interrupted')
        process.kill()
        await process.communicate()
        raise
    finally:
        return response


async def handle_index_page(request):
    """Handle index page."""

    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()

    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    app = web.Application()
    app.args = create_parser().parse_args()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)

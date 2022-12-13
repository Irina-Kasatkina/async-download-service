# coding=utf-8

import aiofiles
import asyncio
import logging
import os
from aiohttp import web


logging.basicConfig(level = logging.DEBUG)

CHUNK_SIZE = 1024


async def archive(request):
    archive_hash = request.match_info.get('archive_hash', '')
    archive_path = os.path.join(os.getcwd(), 'test_photos', archive_hash)
    if not archive_hash or not os.path.exists(archive_path):
        raise web.HTTPNotFound(text='Архив не существует или был удален')

    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/html'
    response.headers['Content-Disposition'] = f'attachment; filename="wedding.zip"'
    await response.prepare(request)

    args = ['-qr', '-', '.']
    process: Process = await asyncio.create_subprocess_exec(
        'zip',
        *args,
        cwd=archive_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    while not process.stdout.at_eof():
        zip_chunk = await process.stdout.read(CHUNK_SIZE)
        logging.info('Sending archive chunk ...')
        await response.write(zip_chunk)
    return response



async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)

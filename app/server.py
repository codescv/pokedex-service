import logging

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
import uvicorn, aiohttp, asyncio
from io import BytesIO

from fastai import *
from fastai.vision import *

import pandas as pd

logger = logging.getLogger(__name__)

model_file_url = 'https://storage.googleapis.com/swift-district-235306.appspot.com/pokedex/models/export.pkl'
model_file_name = 'export'
path = Path(__file__).parent

app = Starlette()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_headers=['X-Requested-With', 'Content-Type'])
app.mount('/static', StaticFiles(directory='app/static'))

pokemon_stats = pd.read_csv(path/'models'/'pokemon_stat.csv')
e2c = {}
for e_name, c_name in zip(pokemon_stats['English'], pokemon_stats['Simplified Chinese']):
  e2c[e_name] = c_name

async def download_file(url, dest):
    if dest.exists(): return
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.read()
            with open(dest, 'wb') as f: f.write(data)

async def setup_learner():
    await download_file(model_file_url, path/'models'/f'{model_file_name}.pkl')
    learn = load_learner(path/'models')
    logger.warn('loaded model: %s', learn)
    return learn

loop = asyncio.get_event_loop()
tasks = [asyncio.ensure_future(setup_learner())]
learn = loop.run_until_complete(asyncio.gather(*tasks))[0]
loop.close()

@app.route('/')
def index(request):
    html = path/'view'/'index.html'
    return HTMLResponse(html.open().read())

@app.route('/analyze', methods=['POST'])
async def analyze(request):
    data = await request.form()
    img_bytes = await (data['file'].read())
    img = open_image(BytesIO(img_bytes))
    cat = learn.predict(img)[0].obj
    logger.info('analyze result: %s', cat)
    return JSONResponse({'result': cat + ' ' + e2c[cat]})

if __name__ == '__main__':
    if 'serve' in sys.argv: uvicorn.run(app, host='0.0.0.0', port=8080)


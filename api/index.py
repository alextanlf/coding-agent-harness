from mangum import Mangum
from web.app import app

handler = Mangum(app, lifespan="off")

from fastapi import FastAPI, APIRouter, Request
from fastapi.security import HTTPBasic, HTTPBearer
from starlette.status import HTTP_504_GATEWAY_TIMEOUT
from fastapi.responses import JSONResponse
from starlette_discord import DiscordOAuthClient
from starlette.responses import RedirectResponse
from supabase import create_client, Client
from cryptography.fernet import Fernet
import asyncio
import config

client_id = config.OAUTH2_CLIENT_ID
client_secret = config.OAUTH2_CLIENT_SECRET
redirect_uri = config.OAUTH2_REDIRECT_URI
SUPABASE_URL = config.SUPABASE_URL
SUPABASE_KEY = config.SUPABASE_KEY

router = APIRouter()
app = FastAPI(title='fastAPI', description='Discord Authentication API')
security = HTTPBasic()
token_auth_scheme = HTTPBearer()
discord_client = DiscordOAuthClient(client_id, client_secret, redirect_uri)

# Set timeout middleware [OPTIONAL: Uncomment to use]
REQUEST_TIMEOUT_ERROR = 30  # Seconds
@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    try:
        return await asyncio.wait_for(call_next(request), timeout=REQUEST_TIMEOUT_ERROR)
    except asyncio.TimeoutError:
        return JSONResponse({'detail': 'Request processing time excedeed limit'},
                            status_code=HTTP_504_GATEWAY_TIMEOUT)


@app.get('/login')
async def start_login(uuid: str, api_key: str):
    # Check if API Key matches
    if api_key == config.API_KEY:
        # Encode User ID
        fernet = Fernet(config.FERNET_KEY)
        encoded_uuid = fernet.encrypt(uuid.encode()).hex()
        # Return User to OAuth Screen with encoded User ID as state
        return discord_client.redirect(state=encoded_uuid)
    else:
        return {"invalid key"}


@app.get('/callback')
async def finish_login(code: str, state: str):
    # Get Discord ID
    user = await discord_client.login(code)
    # Decode UUID
    fernet = Fernet(config.FERNET_KEY)
    uuid = fernet.decrypt(bytes.fromhex(state)).decode()
    # Update User in Supabase
    supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    data = supabase.table("users").update({"discord_id": f"{user}"}).eq("id", f"{uuid}").execute()
    # After authentication redirect the user here
    response = RedirectResponse(url='http://localhost:3000/')
    return response

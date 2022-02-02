import asyncio
import discord
from discord.ext import commands
from discord.ext import tasks
from discord.ext.commands import has_permissions
from supabase import create_client, Client
import config
import json
import traceback

intents = discord.Intents.all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!', intents=intents)


async def get_subscribers():
    # Login to supabase
    supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    # Get users
    data = supabase.table('users').select('*').execute()
    data = json.loads(data.json())
    discord_user_list = []
    match = {}
    # Check if user is subscribed
    for user in data['data']:
        uuid = user['id']
        try:
            subscriptions = supabase.table('subscriptions').select('price_id', 'status').eq("user_id", f"{uuid}").execute().json()
            status = json.loads(subscriptions)['data'][0]['status']
            tier = json.loads(subscriptions)['data'][0]['price_id']
            match['uuid'] = uuid
            match['status'] = status
            match['tier'] = tier
            # Check if user has connected discord
            if user['discord_id']:
                match['discord_id'] = user['discord_id']
            else:
                match['discord_id'] = None
            discord_user_list.append(match)
        except IndexError:
            # print(f"No subscription found for user: {uuid}")
            pass
        except Exception:
            traceback.print_exc()

    # Basic level price ID (from Stripe)
    basic_price_id = config.BASIC_PRICE_ID
    # Premium level price ID (from Stripe)
    premium_price_id = config.PREMIUM_PRICE_ID
    # Get list of basic users
    basic_tier_list = list(filter(lambda d: d['tier'] in basic_price_id, discord_user_list))
    basic_tier_list = [str(d['discord_id']) for d in basic_tier_list]
    # Get list of premium users
    premium_tier_list = list(filter(lambda d: d['tier'] in premium_price_id, discord_user_list))
    premium_tier_list = [str(d['discord_id']) for d in premium_tier_list]
    return basic_tier_list, premium_tier_list


@bot.event
async def on_ready():
    print(f"Bot {bot.user} has connected to Discord!")
    # Run bot on startup
    if not my_background_task.is_running():
        my_background_task.start()


@tasks.loop(seconds=300)  # Check every 300 seconds (5 min)
@has_permissions(manage_roles=True)
async def my_background_task():
    # Set manually allowed users
    premium_manual = config.PREMIUM_MANUAL
    basic_manual = config.BASIC_MANUAL
    # Get subscribers from supabase
    basic_tier_list, premium_tier_list = await get_subscribers()
    # Combine lists
    premium_tier_list = basic_tier_list+premium_manual
    basic_tier_list = basic_tier_list+basic_manual
    # Get non-bot members of server
    guild = bot.get_guild(config.DISCORD_GUILD_ID) # Integer Value
    humans = [m for m in guild.members if not m.bot]
    for human in humans:
        # Get user's roles
        role_list = [r.name for r in human.roles]
        # Get user's full discord name (with # sign and number)
        full_name = human.name+"#"+human.discriminator

        # Give Premium Access
        if full_name in premium_tier_list:
            role = discord.utils.get(human.guild.roles, name="Premium")
            if role.name not in role_list:
                print(f'Giving premium to {full_name}')
                await human.add_roles(role)

        # Remove Premium Access
        if full_name not in premium_tier_list:
            role = discord.utils.get(human.guild.roles, name="Premium")
            if role.name in role_list:
                print(f'Removing premium from {full_name}')
                await human.remove_roles(role)

        # Give Basic Access
        if full_name in basic_tier_list:
            role = discord.utils.get(human.guild.roles, name="Basic")
            if role.name not in role_list:
                print(f'Giving basic to {full_name}')
                await human.add_roles(role)

        # Remove Basic Access
        if full_name not in basic_tier_list:
            role = discord.utils.get(human.guild.roles, name="Basic")
            if role.name in role_list:
                print(f'Removing basic from {full_name}')
                await human.remove_roles(role)

# Run the bot
bot.run(config.DISCORD_TOKEN)

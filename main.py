import os
import discord
import aiohttp
import random
from discord.ext import commands
from urllib.parse import urlparse
from flask import Flask
from threading import Thread

# Flask server untuk health check
flask_app = Flask(__name__)
@flask_app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

# Jalankan Flask saat bot ready
@bot.event
async def on_ready():
    Thread(target=run_flask).start()
    print(f"Bot {bot.user} is online!")

# Bot Setup
TOKEN = os.getenv("DISCORD_TOKEN")
API_BASE = "https://fless.ps.fhgdps.com/dashboard/api/"

# Konfigurasi Cobalt
USE_COBALT = True
COBALT_APIS = ['https://cobalt.gcs.icu']

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="F ", intents=intents)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="F help | FreedomGDPS Bot"))
    print(f"Bot {bot.user} is online!")

# Helper async HTTP methods
def _format_error(e): 
    return f"❌ Error: {e}"

async def api_post(session, endpoint, data):
    url = API_BASE + endpoint
    async with session.post(url, data=data) as resp:
        text = await resp.text()
        return resp.status, text

async def api_get(session, endpoint, params=None):
    url = API_BASE + endpoint
    async with session.get(url, params=params) as resp:
        text = await resp.text()
        return resp.status, text

async def download_with_cobalt(youtube_url):
    if not USE_COBALT:
        return {"error": "Cobalt upload is disabled"}
    
    if not COBALT_APIS:
        return {"error": "No Cobalt APIs configured"}
    
    api_url = random.choice(COBALT_APIS)
    endpoint = f"{api_url}/api/json"
    
    payload = {
        "url": youtube_url,
        "vCodec": "h264",
        "aFormat": "mp3",
        "isAudioOnly": True,
        "isNoTTWatermark": True,
        "dubLang": False
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            # Step 1: Request ke Cobalt API
            async with session.post(endpoint, json=payload) as resp:
                data = await resp.json()
                
                if data.get("status") == "error":
                    return {"error": data.get("text", "Unknown error from Cobalt API")}
                
                if not data.get("url"):
                    return {"error": "No download URL returned from Cobalt"}
                
                # Step 2: Download file audio
                audio_url = data['url']
                async with session.get(audio_url) as audio_resp:
                    if audio_resp.status != 200:
                        return {"error": f"Failed to download audio: {audio_resp.status}"}
                    
                    # Ekstrak nama file
                    parsed_url = urlparse(audio_url)
                    filename = os.path.basename(parsed_url.path)
                    if not filename.endswith('.mp3'):
                        filename = f"{filename}.mp3"
                    
                    # Baca konten file
                    content = await audio_resp.read()
                    return {
                        "success": True,
                        "filename": filename,
                        "content": content,
                        "title": data.get("title", "Unknown"),
                        "duration": data.get("duration", 0)
                    }
                    
        except aiohttp.ClientError as e:
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"error": f"An error occurred: {str(e)}"}

# ===== Commands =====
@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latency: {round(bot.latency*1000)}ms")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"🧹 Deleted {len(deleted)} messages.", delete_after=5)

@clear.error
async def clear_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You lack permission to clear messages.")

@bot.command()
async def userinfo(ctx, member: discord.Member=None):
    member = member or ctx.author
    embed = discord.Embed(title=f"User Info: {member}", color=discord.Color.blue())
    embed.set_thumbnail(url=member.avatar.url)
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d"))
    await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    g = ctx.guild
    embed = discord.Embed(title="Server Info", color=discord.Color.gold())
    embed.set_thumbnail(url=g.icon.url if g.icon else None)
    embed.add_field(name="Name", value=g.name)
    embed.add_field(name="Members", value=g.member_count)
    embed.add_field(name="Owner", value=str(g.owner))
    await ctx.send(embed=embed)

@bot.command()
async def botinfo(ctx):
    embed = discord.Embed(title="FreedomGDPS Bot", color=discord.Color.purple())
    embed.add_field(name="Website", value="https://fless.ps.fhgdps.com")
    await ctx.send(embed=embed)

@bot.command()
async def gtw(ctx, *, msg: str):
    await ctx.send(msg)

@bot.command()
async def avatar(ctx, member: discord.Member=None):
    member = member or ctx.author
    embed = discord.Embed(title=f"Avatar: {member}")
    embed.set_image(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def uploadsong(ctx, name: str = None, id: int = None, size: float = None, 
                    author: str = None, download: str = None, youtube_url: str = None):
    """
    Upload lagu dengan dua cara:
    1. F uploadsong <name> <id> <size> <author> <download> - Upload langsung dengan detail
    2. F uploadsong <youtube_url> - Download dari YouTube via Cobalt
    """
    
    if youtube_url:
        # Mode download dari YouTube
        if not USE_COBALT:
            return await ctx.send("❌ Fitur download dari YouTube dinonaktifkan")
            
        processing_msg = await ctx.send("⏳ Mengunduh lagu dari YouTube, harap tunggu...")
        
        result = await download_with_cobalt(youtube_url)
        if not result.get("success"):
            return await processing_msg.edit(content=f"❌ Gagal: {result.get('error', 'Unknown error')}")
        
        await processing_msg.edit(content=f"✅ Berhasil mengunduh: **{result['title']}**\n📤 Mengupload ke Discord...")
        
        # Kirim file langsung dari memory tanpa save ke disk
        await ctx.send(
            content=f"🎵 **{result['title']}**",
            file=discord.File(
                filename=result['filename'],
                fp=result['content']
            )
        )
        await processing_msg.edit(content=f"🎵 **{result['title']}** berhasil diupload!")
    else:
        # Mode upload manual
        if not all([name, id, size, author, download]):
            return await ctx.send("❌ Format: `F uploadsong <name> <id> <size> <author> <download>` atau `F uploadsong <youtube_url>`")
            
        async with aiohttp.ClientSession() as session:
            data = {
                "songName": name, 
                "songID": id, 
                "songSize": size, 
                "songAuthor": author, 
                "download": download
            }
            status, text = await api_post(session, "addSong.php", data)
            
        # split long text
        for chunk in [text[i:i+2000] for i in range(0, len(text), 2000)]:
            await ctx.send(chunk)

@bot.command()
async def searchlevel(ctx, *, query: str):
    async with aiohttp.ClientSession() as session:
        status, text = await api_post(session, "searchLevel.php", {"query": query})
    for chunk in [text[i:i+2000] for i in range(0, len(text), 2000)]:
        await ctx.send(chunk)

@bot.command()
async def whorated(ctx, level_id: int):
    async with aiohttp.ClientSession() as session:
        status, text = await api_post(session, "whoRated.php", {"levelID": level_id})
    for chunk in [text[i:i+2000] for i in range(0, len(text), 2000)]:
        await ctx.send(chunk)

@bot.command()
async def stats(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://fless.ps.fhgdps.com/dashboard/api/stats.php") as resp:
            data = await resp.json()

    if not data.get("success"):
        await ctx.send("Gagal mengambil data statistik.")
        return

    stats = data["stats"]
    embed = discord.Embed(title="FlessGDPS Stats", color=0x00ffcc)
    embed.add_field(name="Users", value=f'Total: **{stats["users"]["total"]}**\nActive: **{stats["users"]["active"]}**', inline=True)
    embed.add_field(name="Levels", value=(
        f'Total: **{stats["levels"]["total"]}**\n'
        f'Rated: {stats["levels"]["rated"]}, Featured: {stats["levels"]["featured"]}\n'
        f'Epic: {stats["levels"]["epic"]}, Legendary: {stats["levels"]["legendary"]}, Mythic: {stats["levels"]["mythic"]}\n'
        f'Dailies: {stats["levels"]["special"]["dailies"]}, Weeklies: {stats["levels"]["special"]["weeklies"]}'
    ), inline=False)
    # ... (field lainnya tetap sama)
    await ctx.send(embed=embed)

@bot.command()
async def profile(ctx, username: str):
    async with aiohttp.ClientSession() as session:
        status, text = await api_post(session, "profile.php", {"username": username})
    for chunk in [text[i:i+2000] for i in range(0, len(text), 2000)]:
        await ctx.send(chunk)

@bot.command()
async def login(ctx, username: str, password: str):
    await ctx.send("⚠️ Jangan gunakan command ini di channel publik!")
    async with aiohttp.ClientSession() as session:
        status, text = await api_post(session, "login.php", {"userName": username, "password": password})
    await ctx.author.send(f"Login result: {text[:2000]}")  # Kirim via DM

@bot.command()
async def createembed(ctx, *, arg):
    parts = [p.strip() for p in arg.split("|")]
    if len(parts) < 2:
        return await ctx.send("❌ Use format: Title | Desc | #hex (opt) | thumbURL (opt) | footer (opt)")
    title, desc = parts[0], parts[1]
    color = int(parts[2].lstrip("#"),16) if len(parts)>=3 else 0x2f3136
    embed = discord.Embed(title=title, description=desc, color=color)
    if len(parts)>=4 and parts[3].startswith("http"): embed.set_thumbnail(url=parts[3])
    if len(parts)>=5: embed.set_footer(text=parts[4])
    await ctx.send(embed=embed)

@bot.command()
async def menu(ctx):
    cmds = ["ping","clear","userinfo","serverinfo","botinfo","gtw","avatar","uploadsong","searchlevel","whorated","stats","profile","login","createembed"]
    embed = discord.Embed(title="Available Commands", color=0x7289da)
    embed.description = "\n".join(f"• `F {c}`" for c in cmds)
    await ctx.send(embed=embed)

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN is not set.")
    else:
        bot.run(TOKEN)

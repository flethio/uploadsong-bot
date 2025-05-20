import os
import discord
import aiohttp
from discord.ext import commands

# Bot Setup
TOKEN = os.getenv("DISCORD_TOKEN")
API_BASE = "https://fless.ps.fhgdps.com/dashboard/api/"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="F ", intents=intents)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="F help | FreedomGDPS Bot"))
    print(f"Bot {bot.user} is online!")

# Helper async HTTP methods
def _format_error(e): return f"❌ Error: {e}"

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
    embed.set_thumbnail(url=g.icon.url if g.icon else discord.Embed.Empty)
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
async def uploadsong(ctx, name: str, id: int, size: float, author: str, download: str):
    async with aiohttp.ClientSession() as session:
        data = {"songName": name, "songID": id, "songSize": size, "songAuthor": author, "download": download}
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
    users = stats["users"]
    levels = stats["levels"]
    downloads = stats["downloads"]
    objects = stats["objects"]
    likes = stats["likes"]
    comments = stats["comments"]
    stars = stats["gained_stars"]
    cp = stats["creator_points"]
    bans = stats["bans"]

    embed = discord.Embed(title="FlessGDPS Stats", color=0x00ffcc)
    embed.add_field(name="Users", value=f'Total: **{users["total"]}**\nActive: **{users["active"]}**', inline=True)
    embed.add_field(name="Levels", value=(
        f'Total: **{levels["total"]}**\n'
        f'Rated: {levels["rated"]}, Featured: {levels["featured"]}\n'
        f'Epic: {levels["epic"]}, Legendary: {levels["legendary"]}, Mythic: {levels["mythic"]}\n'
        f'Dailies: {levels["special"]["dailies"]}, Weeklies: {levels["special"]["weeklies"]}'
    ), inline=False)
    embed.add_field(name="Downloads", value=f'Total: {downloads["total"]}\nAvg: {downloads["average"]:.2f}', inline=True)
    embed.add_field(name="Objects", value=f'Total: {objects["total"]}\nAvg: {objects["average"]:.2f}', inline=True)
    embed.add_field(name="Likes", value=f'Total: {likes["total"]}\nAvg: {likes["average"]:.2f}', inline=True)
    embed.add_field(name="Comments", value=f'Total: {comments["total"]}\nPosts: {comments["posts"]}, Replies: {comments["post_replies"]}', inline=False)
    embed.add_field(name="Stars", value=f'Total: {stars["total"]}\nAvg: {stars["average"]:.2f}', inline=True)
    embed.add_field(name="Creator Points", value=f'Total: {cp["total"]}\nAvg: {cp["average"]:.2f}', inline=True)
    embed.add_field(name="Bans", value=f'Total: {bans["total"]}\nLeaderboard Bans: {bans["banTypes"]["leaderboardBans"]}', inline=False)

    await ctx.send(embed=embed)
@bot.command()
async def profile(ctx, username: str):
    async with aiohttp.ClientSession() as session:
        status, text = await api_post(session, "profile.php", {"username": username})
    for chunk in [text[i:i+2000] for i in range(0, len(text), 2000)]:
        await ctx.send(chunk)

@bot.command()
async def login(ctx, username: str, password: str):
    async with aiohttp.ClientSession() as session:
        status, text = await api_post(session, "login.php", {"userName": username, "password": password})
    for chunk in [text[i:i+2000] for i in range(0, len(text), 2000)]:
        await ctx.send(chunk)

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
    await ctx.send("Available commands: " + ", ".join(f"F {c}" for c in cmds))

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN is not set.")
    else:
        bot.run(TOKEN)
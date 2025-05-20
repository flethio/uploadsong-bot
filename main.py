import os
import discord
import aiohttp
import yt_dlp as youtube_dl
from discord.ext import commands
from typing import Optional

# Bot Setup
TOKEN = os.getenv("DISCORD_TOKEN")
API_BASE = "https://fless.ps.fhgdps.com/dashboard/api/"
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="F ", intents=intents)

# ===== Upgrade 1: Audio Processing Helper =====
class AudioConverter:
    @staticmethod
    async def download_audio(url: str) -> Optional[dict]:
        ytdl_format_options = {
            'format': 'bestaudio/best',
            'outtmpl': '%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        try:
            with youtube_dl.YoutubeDL(ytdl_format_options) as ytdl:
                info = ytdl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown Title'),
                    'url': info['url'],
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', '')
                }
        except Exception as e:
            print(f"Download error: {e}")
            return None

# ===== Upgrade 2: Enhanced Upload Command =====
@bot.command()
async def song(ctx, url: str):
    """Upload song from YouTube/TikTok/SoundCloud link"""
    # Auto-delete command message
    await ctx.message.delete()
    
    converter = AudioConverter()
    data = await converter.download_audio(url)
    
    if not data:
        return await ctx.send(embed=discord.Embed(
            title="❌ Error",
            description="Failed to process audio link!",
            color=discord.Color.red()
        ))
    
    loading_msg = await ctx.send(embed=discord.Embed(
        title="⏳ Processing...",
        description="Downloading and converting audio...",
        color=discord.Color.orange()
    ))
    
    try:
        async with aiohttp.ClientSession() as session:
            # Upload to GDPS API
            post_data = {
                "songName": data['title'],
                "songURL": data['url'],
                "duration": data['duration'],
                "userID": ctx.author.id
            }
            status, response = await api_post(session, "addSong.php", post_data)
            
            # Edit loading message with result
            embed = discord.Embed(
                title="✅ Song Added" if status == 200 else "❌ Upload Failed",
                description=f"**{data['title']}**\nDuration: {data['duration']}s",
                color=discord.Color.green() if status == 200 else discord.Color.red()
            )
            embed.set_thumbnail(url=data['thumbnail'])
            embed.add_field(name="Status Code", value=str(status))
            embed.add_field(name="API Response", value=response[:1000], inline=False)
            
            await loading_msg.edit(embed=embed)
            
    except Exception as e:
        await loading_msg.edit(embed=discord.Embed(
            title="❌ Critical Error",
            description=str(e),
            color=discord.Color.red()
        ))

# ===== Upgrade 3: Enhanced Error Handling =====
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(embed=discord.Embed(
            title="❌ Unknown Command",
            description=f"Use `F menu` for available commands",
            color=discord.Color.red()
        ))
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(
            title="❌ Missing Arguments",
            description=f"Correct usage: `F {ctx.command.name} {ctx.command.signature}`",
            color=discord.Color.red()
        ))
    else:
        await ctx.send(embed=discord.Embed(
            title="❌ Unexpected Error",
            description=str(error),
            color=discord.Color.red()
        ))

# ===== Upgrade 4: Command Cooldowns =====
from discord.ext.commands import BucketType

@bot.command()
@commands.cooldown(1, 30, BucketType.user)
async def whorated(ctx, level_id: int):
    # Existing code remains the same
    ...

# ===== Upgrade 5: Enhanced Profile Command =====
@bot.command()
async def profile(ctx, username: str):
    async with aiohttp.ClientSession() as session:
        status, text = await api_post(session, "profile.php", {"username": username})
        
    if status != 200:
        return await ctx.send(embed=discord.Embed(
            title="❌ Profile Error",
            description=text,
            color=discord.Color.red()
        ))
    
    try:
        profile_data = json.loads(text)
        embed = discord.Embed(
            title=f"👤 {username}'s Profile",
            color=discord.Color.blue()
        )
        embed.add_field(name="Stars", value=profile_data.get('stars', 'N/A'))
        embed.add_field(name="Coins", value=profile_data.get('coins', 'N/A'))
        embed.add_field(name="Rank", value=profile_data.get('rank', 'N/A'))
        embed.set_thumbnail(url=profile_data.get('icon', ''))
        await ctx.send(embed=embed)
        
    except json.JSONDecodeError:
        await ctx.send(f"```{text[:1900]}```")

# ===== Upgrade 6: Security Improvement =====
@bot.command()
@commands.has_permissions(administrator=True)
async def login(ctx, username: str, password: str):
    await ctx.message.delete()
    # Existing code remains but now hidden
    ...

# ===== Existing Code Below (DO NOT MODIFY) =====
# [All existing commands and functions remain unchanged below this line]
# ...

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN is not set.")
    else:
        bot.run(TOKEN)
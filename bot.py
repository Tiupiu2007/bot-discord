import asyncio
import os
from dataclasses import dataclass, field
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("Manca DISCORD_TOKEN nel file .env")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch1",
    "source_address": "0.0.0.0",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


@dataclass
class GuildPlayer:
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    task: Optional[asyncio.Task] = None
    current: Optional[str] = None


players: dict[int, GuildPlayer] = {}


def get_player(guild_id: int) -> GuildPlayer:
    if guild_id not in players:
        players[guild_id] = GuildPlayer()
    return players[guild_id]


async def extract_track(query: str) -> dict:
    def _extract():
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            data = ydl.extract_info(query, download=False)
            if "entries" in data:
                data = next((entry for entry in data["entries"] if entry), None)
            if not data:
                raise ValueError("Non ho trovato nessun risultato.")
            return {
                "title": data.get("title") or "Brano sconosciuto",
                "url": data["url"],
                "webpage_url": data.get("webpage_url", query),
            }

    return await asyncio.to_thread(_extract)


async def player_worker(guild: discord.Guild, state: GuildPlayer):
    try:
        while True:
            try:
                track = await asyncio.wait_for(state.queue.get(), timeout=180)
            except asyncio.TimeoutError:
                voice = guild.voice_client
                if voice and voice.is_connected() and not voice.is_playing() and not voice.is_paused():
                    await voice.disconnect()
                break

            voice = guild.voice_client
            if not voice or not voice.is_connected():
                state.queue.task_done()
                break

            state.current = track["title"]
            loop = asyncio.get_running_loop()
            finished = loop.create_future()

            def after_playback(error):
                if error:
                    print(f"Errore riproduzione: {error}")
                loop.call_soon_threadsafe(
                    lambda: (not finished.done()) and finished.set_result(None)
                )

            try:
                source = discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTIONS)
                voice.play(source, after=after_playback)
                await finished
            except Exception as error:
                print(f"Impossibile riprodurre {track['title']}: {error}")
            finally:
                state.current = None
                state.queue.task_done()
    finally:
        state.task = None


async def ensure_voice(interaction: discord.Interaction) -> discord.VoiceClient:
    if not interaction.guild:
        raise app_commands.AppCommandError("Questo comando può essere usato solo in un server.")
    if not interaction.user.voice or not interaction.user.voice.channel:
        raise app_commands.AppCommandError("Devi essere in un canale vocale prima di usare questo comando.")

    channel = interaction.user.voice.channel
    voice = interaction.guild.voice_client

    if voice and voice.is_connected():
        if voice.channel != channel:
            raise app_commands.AppCommandError("Devi essere nello stesso canale vocale del bot.")
        return voice

    return await channel.connect()


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Connesso come {bot.user}. Comandi slash sincronizzati: {len(synced)}")
    except Exception as error:
        print(f"Errore sincronizzazione comandi: {error}")


@bot.tree.command(name="play", description="Riproduce un link YouTube o cerca un brano per titolo.")
@app_commands.describe(query="Link YouTube oppure titolo del brano")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer(thinking=True)

    try:
        voice = await ensure_voice(interaction)
        track = await extract_track(query)
        state = get_player(interaction.guild_id)
        await state.queue.put(track)

        if not state.task or state.task.done():
            state.task = asyncio.create_task(player_worker(interaction.guild, state))

        position = state.queue.qsize()
        if voice.is_playing() or voice.is_paused() or position > 1:
            message = f"🎵 **{track['title']}** aggiunto alla coda (posizione {position})."
        else:
            message = f"🎵 Preparato **{track['title']}**."
        await interaction.followup.send(message)
    except Exception as error:
        await interaction.followup.send(f"Non sono riuscito ad avviare la riproduzione: {error}")


@bot.tree.command(name="skip", description="Salta il brano attuale.")
async def skip(interaction: discord.Interaction):
    voice = interaction.guild.voice_client if interaction.guild else None
    if not voice or not voice.is_connected() or not voice.is_playing():
        await interaction.response.send_message("Non c'è nessun brano in riproduzione.", ephemeral=True)
        return
    if not interaction.user.voice or interaction.user.voice.channel != voice.channel:
        await interaction.response.send_message("Devi essere nel canale vocale del bot.", ephemeral=True)
        return
    voice.stop()
    await interaction.response.send_message("⏭️ Brano saltato.")


@bot.tree.command(name="pause", description="Mette in pausa la riproduzione.")
async def pause(interaction: discord.Interaction):
    voice = interaction.guild.voice_client if interaction.guild else None
    if not voice or not voice.is_playing():
        await interaction.response.send_message("Non c'è nessun brano da mettere in pausa.", ephemeral=True)
        return
    if not interaction.user.voice or interaction.user.voice.channel != voice.channel:
        await interaction.response.send_message("Devi essere nel canale vocale del bot.", ephemeral=True)
        return
    voice.pause()
    await interaction.response.send_message("⏸️ Riproduzione in pausa.")


@bot.tree.command(name="resume", description="Riprende la riproduzione.")
async def resume(interaction: discord.Interaction):
    voice = interaction.guild.voice_client if interaction.guild else None
    if not voice or not voice.is_paused():
        await interaction.response.send_message("La riproduzione non è in pausa.", ephemeral=True)
        return
    if not interaction.user.voice or interaction.user.voice.channel != voice.channel:
        await interaction.response.send_message("Devi essere nel canale vocale del bot.", ephemeral=True)
        return
    voice.resume()
    await interaction.response.send_message("▶️ Riproduzione ripresa.")


@bot.tree.command(name="stop", description="Ferma la musica, svuota la coda e disconnette il bot.")
async def stop(interaction: discord.Interaction):
    voice = interaction.guild.voice_client if interaction.guild else None
    if not voice or not voice.is_connected():
        await interaction.response.send_message("Il bot non è collegato a un canale vocale.", ephemeral=True)
        return
    if not interaction.user.voice or interaction.user.voice.channel != voice.channel:
        await interaction.response.send_message("Devi essere nel canale vocale del bot.", ephemeral=True)
        return

    state = get_player(interaction.guild_id)
    while not state.queue.empty():
        try:
            state.queue.get_nowait()
            state.queue.task_done()
        except asyncio.QueueEmpty:
            break

    voice.stop()
    if state.task and not state.task.done():
        state.task.cancel()
    state.task = None
    await voice.disconnect()
    await interaction.response.send_message("⏹️ Riproduzione fermata, coda svuotata e bot disconnesso.")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    message = str(error)
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


bot.run(TOKEN)

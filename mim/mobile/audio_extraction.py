"""
Agente 1 - AudioExtractionService
Usa mutagen para extrair TODOs os metadados de arquivos de áudio.
"""
import hashlib
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from mutagen import File as MutagenFile
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.id3 import ID3
from mutagen.mp4 import MP4

from mim.mobile.audio_metadata import (
    AudioMetadata, AudioCodec, ReplayGain, ArtworkInfo,
    KeyEnum, ModeEnum,
)

logger = logging.getLogger(__name__)


def _detect_codec(path: str) -> AudioCodec:
    ext = Path(path).suffix.lower()
    mapping = {
        ".mp3": AudioCodec.MP3,
        ".flac": AudioCodec.FLAC,
        ".wav": AudioCodec.WAV,
        ".aac": AudioCodec.AAC,
        ".ogg": AudioCodec.OGG,
        ".opus": AudioCodec.OPUS,
        ".wma": AudioCodec.WMA,
        ".m4a": AudioCodec.M4A,
        ".mp4": AudioCodec.M4A,
    }
    return mapping.get(ext, AudioCodec.UNKNOWN)


def _get_replaygain(tags) -> Optional[ReplayGain]:
    rg_track = tags.get("rg_track_gain", [""])[0]
    rg_album = tags.get("rg_album_gain", [""])[0]
    peak_track = tags.get("rg_track_peak", [""])[0]
    peak_album = tags.get("rg_album_peak", [""])[0]
    try:
        if rg_track and peak_track:
            return ReplayGain(
                track_gain_db=float(rg_track.replace("< ", "").replace(" dB>", "")),
                track_peak=float(peak_track),
            )
    except (ValueError, IndexError):
        pass
    return None


def _extract_key_and_mode(tags) -> tuple[Optional[str], Optional[KeyEnum], Optional[ModeEnum]]:
    """Tenta extrair key e mode de várias fontes."""
    # Try ID3 COMM (comments) for key info
    key_str = None
    for key in ["TMKEY", "TCOMP", "key", " Musical Key"]:
        val = tags.get(key, [""])[0].strip()
        if val:
            key_str = val
            break

    if not key_str:
        return None, None, None

    # Normalize common formats
    key_str = key_str.strip()
    major_indicators = ["", "M", " Maj", " Major"]
    minor_indicators = ["m", " m", " min", " Minor"]

    mode = ModeEnum.MAJOR
    for ind in minor_indicators:
        if key_str.endswith(ind):
            mode = ModeEnum.MINOR
            key_str = key_str[:-len(ind)]
            break

    # Try to match key
    key_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    for kn in key_names:
        if key_str == kn or key_str.lower() == kn.lower():
            return key_str, KeyEnum(kn), mode

    return key_str, None, mode


def _extract_artwork(tags) -> Optional[ArtworkInfo]:
    """Extrai artwork dos tags."""
    try:
        if isinstance(tags, ID3):
            for frame in tags.values():
                if hasattr(frame, "data") and len(frame.data) > 0:
                    mime = "image/jpeg" if isinstance(frame, __import__('mutagen.id3', fromlist=['APIC']).APIC) else "image/png"
                    return ArtworkInfo(
                        mime_type=mime,
                        width=getattr(frame, "width", 0),
                        height=getattr(frame, "height", 0),
                        depth=getattr(frame, "depth", 24),
                        size_bytes=len(frame.data),
                        data=frame.data,
                    )
        elif hasattr(tags, "picture"):
            pic = tags.picture
            return ArtworkInfo(
                mime_type=pic.mime or "image/jpeg",
                width=pic.width,
                height=pic.height,
                depth=pic.depth,
                size_bytes=len(pic.data),
                data=pic.data,
            )
    except Exception as e:
        logger.debug(f"Artwork extraction failed: {e}")
    return None


class AudioExtractionService:
    """
    Extrai todos os metadados de arquivos de áudio usando mutagen.
    Stateless, thread-safe, com cache LRU opcional.
    """

    def __init__(self, enable_cache: bool = True, max_cache_size: int = 1000):
        self._enable_cache = enable_cache
        if enable_cache:
            self._extract_cached = lru_cache(maxsize=max_cache_size)(self._do_extract)
        else:
            self._extract_cached = self._do_extract

    def extract(self, path: str) -> AudioMetadata:
        """Extrai metadados de um arquivo de áudio."""
        return self._extract_cached(path)

    def _do_extract(self, path: str) -> AudioMetadata:
        path = str(Path(path).resolve())
        codec = _detect_codec(path)
        audio = None
        try:
            audio = MutagenFile(path, easy=True)
        except Exception:
            try:
                audio = MutagenFile(path, easy=False)
            except Exception as e:
                logger.warning(f"Cannot open audio file {path}: {e}")
                return AudioMetadata(path=path, codec=codec, duration_ms=0)

        if audio is None:
            return AudioMetadata(path=path, codec=codec, duration_ms=0)

        length_ms = int(getattr(audio, "info", None) and getattr(audio.info, "length", 0) * 1000)

        # Raw tags
        raw_tags = {}
        if hasattr(audio, "tags") and audio.tags:
            for k, v in audio.tags.items():
                raw_tags[k] = v

        # Common tags (mutagen standardizes these)
        title = (audio.get("title") or [None])[0] if audio.get("title") else None
        artist = (audio.get("artist") or [None])[0] if audio.get("artist") else None
        album = (audio.get("album") or [None])[0] if audio.get("album") else None
        album_artist = (audio.get("albumartist") or [None])[0] if audio.get("albumartist") else None
        genre = (audio.get("genre") or [None])[0] if audio.get("genre") else None
        year_str = (audio.get("date") or [None])[0] if audio.get("date") else None
        track_num = (audio.get("tracknumber") or [None])[0] if audio.get("tracknumber") else None
        disc_num = (audio.get("discnumber") or [None])[0] if audio.get("discnumber") else None
        composer = (audio.get("composer") or [None])[0] if audio.get("composer") else None
        lyrics = (audio.get("lyrics") or [None])[0] if audio.get("lyrics") else None
        comment = (audio.get("comment") or [None])[0] if audio.get("comment") else None

        # Parse numeric values
        try:
            track_number = int(track_num.split("/")[0]) if track_num else None
            total_tracks = int(track_num.split("/")[1]) if track_num and "/" in track_num else None
        except (ValueError, IndexError):
            track_number = total_tracks = None

        try:
            disc_number = int(disc_num.split("/")[0]) if disc_num else None
            total_discs = int(disc_num.split("/")[1]) if disc_num and "/" in disc_num else None
        except (ValueError, IndexError):
            disc_number = total_discs = None

        year = int(year_str) if year_str and year_str.isdigit() else None

        # Codec-specific extractions
        bitrate = None
        sample_rate = None
        channels = None
        bit_depth = None
        isrc = None
        mbids = {}
        key_name = None
        key_enum = None
        mode_enum = None
        artwork = None
        replay_gain = None
        bpm = None

        # MP3 specific
        if codec == AudioCodec.MP3 and isinstance(audio, MP3):
            info = audio.info
            bitrate = info.bitrate // 1000 if info and info.bitrate else None
            sample_rate = info.sample_rate
            channels = info.channels
            try:
                from mutagen.mp3 import ID3 as MP3ID3
                id3 = MP3(path, load=False)
                if id3:
                    for frame in id3.values():
                        if hasattr(frame, "text"):
                            text = frame.text[0] if frame.text else ""
                            if isinstance(frame, __import__('mutagen.id3', fromlist=['TRCK']).TRCK):
                                try:
                                    parts = str(text).split("/")
                                    track_number = int(parts[0])
                                    total_tracks = int(parts[1]) if len(parts) > 1 else None
                                except (ValueError, IndexError):
                                    pass
                            elif isinstance(frame, __import__('mutagen.id3', fromlist=['TPOS']).TPOS):
                                try:
                                    parts = str(text).split("/")
                                    disc_number = int(parts[0])
                                    total_discs = int(parts[1]) if len(parts) > 1 else None
                                except (ValueError, IndexError):
                                    pass
                            elif isinstance(frame, __import__('mutagen.id3', fromlist=['TSRC']).TSRC):
                                isrc = text
                            elif isinstance(frame, __import__('mutagen.id3', fromlist=['WXXX']).WXXX):
                                desc = frame.desc.lower()
                                if "musicbrainz" in desc:
                                    mbids["track"] = text
                            elif isinstance(frame, __import__('mutagen.id3', fromlist(['COMM'])).COMM):
                                if frame.desc == "ReplayGain":
                                    pass
            except Exception:
                pass

        # FLAC specific
        elif codec == AudioCodec.FLAC and isinstance(audio, FLAC):
            sample_rate = audio.info.sample_rate
            channels = audio.info.channels
            bit_depth = audio.info.bits_per_sample
            # Parse vorbis tags
            for key, vals in audio.tags.items():
                kl = key.lower()
                if kl == "isrc" and vals:
                    isrc = vals[0]
                elif kl == "musicbrainz_trackid" and vals:
                    mbids["track"] = vals[0]
                elif kl == "musicbrainz_artistid" and vals:
                    mbids["artist"] = vals[0]
                elif kl == "musicbrainz_releaseid" and vals:
                    mbids["release"] = vals[0]
                elif kl == "acoustid_id" and vals:
                    pass  # acoustid handled separately
                elif kl == "replaygain_track_gain":
                    try:
                        replay_gain = ReplayGain(
                            track_gain_db=float(vals[0].replace("<", "").replace(" dB>", "")),
                        )
                    except (ValueError, IndexError):
                        pass
                elif kl == "replaygain_track_peak":
                    if replay_gain:
                        try:
                            replay_gain = ReplayGain(
                                track_peak=float(vals[0]),
                                track_gain_db=replay_gain.track_gain_db,
                            )
                        except ValueError:
                            pass

        # OGG Vorbis
        elif codec == AudioCodec.OGG and isinstance(audio, OggVorbis):
            sample_rate = audio.info.sample_rate
            channels = audio.info.channels
            for key, vals in audio.tags.items():
                kl = key.lower()
                if kl == "isrc" and vals:
                    isrc = vals[0]
                elif kl == "musicbrainz_trackid" and vals:
                    mbids["track"] = vals[0]
                elif kl == "musicbrainz_artistid" and vals:
                    mbids["artist"] = vals[0]
                elif kl == "musicbrainz_releaseid" and vals:
                    mbids["release"] = vals[0]

        # MP4/M4A
        elif codec in (AudioCodec.M4A, AudioCodec.AAC) and isinstance(audio, MP4):
            if audio.get("\xa9alb"):
                album = audio["\xa9alb"][0]
            if audio.get("\xa9ART"):
                artist = audio["\xa9ART"][0]
            if audio.get("\xa9nam"):
                title = audio["\xa9nam"][0]
            if audio.get("----:com.apple:iTunsmbd"):
                try:
                    bpm = float(audio["----:com.apple:iTunsmbd"][0])
                except (ValueError, IndexError):
                    pass

        # Get artwork from codec-specific taggers
        artwork = _extract_artwork(audio)

        # BPM heuristic from tags
        if bpm is None:
            for tag_name in ["BPM", "tmusic", " tempo"]:
                val = raw_tags.get(tag_name)
                if val:
                    try:
                        bpm = float(str(val[0]).strip())
                    except (ValueError, TypeError):
                        pass
                    break

        # Key extraction
        key_name, key_enum, mode_enum = _extract_key_and_mode(raw_tags)
        if not key_name:
            # Try from common tag positions
            for tag in ["TMKEY", "key", " Musical Key", "TKEY"]:
                val = raw_tags.get(tag)
                if val:
                    key_name, key_enum, mode_enum = _extract_key_and_mode({tag: val})
                    break

        # Build result
        return AudioMetadata(
            path=path,
            codec=codec,
            duration_ms=length_ms,
            bitrate_kbps=bitrate,
            sample_rate_hz=sample_rate,
            channels=channels,
            bit_depth=bit_depth,
            title=title,
            artist=artist,
            album=album,
            album_artist=album_artist,
            track_number=track_number,
            disc_number=disc_number,
            total_tracks=total_tracks,
            total_discs=total_discs,
            year=year,
            genre=genre,
            composer=composer,
            comment=comment,
            lyrics=lyrics,
            isrc=isrc,
            musicbrainz_track_id=mbids.get("track"),
            musicbrainz_artist_id=mbids.get("artist"),
            musicbrainz_release_id=mbids.get("release"),
            bpm=bpm,
            key_name=key_name,
            key_enum=key_enum,
            mode_enum=mode_enum,
            replay_gain=replay_gain,
            artwork=artwork,
            raw_tags=raw_tags,
        )

    def get_file_hash(self, path: str, algorithm: str = "sha256") -> str:
        """Calcula hash do arquivo (para fingerprinting)."""
        h = hashlib.new(algorithm)
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
"""
Domain service for audio extraction.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable
from mutagen import File as MutagenFile
from mutagen.id3 import ID3
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from pathlib import Path
import hashlib
from functools import lru_cache


class AudioCodec(str, Enum):
    MP3 = "mp3"
    FLAC = "flac"
    WAV = "wav"
    AAC = "aac"
    OGG = "ogg"
    OPUS = "opus"
    WMA = "wma"
    M4A = "m4a"
    UNKNOWN = "unknown"


class KeyEnum(str, Enum):
    C = "C"
    C_SHARP = "C#"
    D = "D"
    D_SHARP = "D#"
    E = "E"
    F = "F"
    F_SHARP = "F#"
    G = "G"
    G_SHARP = "G#"
    A = "A"
    A_SHARP = "A#"
    B = "B"


class ModeEnum(str, Enum):
    MAJOR = "major"
    MINOR = "minor"


@dataclass(frozen=True)
class ReplayGain:
    track_peak: Optional[float] = None
    track_gain_db: Optional[float] = None
    album_peak: Optional[float] = None
    album_gain_db: Optional[float] = None


@dataclass(frozen=True)
class ArtworkInfo:
    mime_type: str
    width: int
    height: int
    depth: int
    size_bytes: int
    description: str = ""
    data: bytes = b""


@dataclass(frozen=True)
class AudioMetadata:
    """Metadados extraídos de um arquivo de áudio."""
    path: str
    codec: AudioCodec
    duration_ms: int
    bitrate_kbps: Optional[int] = None
    sample_rate_hz: Optional[int] = None
    channels: Optional[int] = None
    bit_depth: Optional[int] = None

    # Tags de metadados
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    album_artist: Optional[str] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    total_tracks: Optional[int] = None
    total_discs: Optional[int] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    composer: Optional[str] = None
    conductor: Optional[str] = None
    comment: Optional[str] = None
    copyright: Optional[str] = None
    lyrics: Optional[str] = None

    # Identificadores
    isrc: Optional[str] = None
    musicbrainz_track_id: Optional[str] = None
    musicbrainz_artist_id: Optional[str] = None
    musicbrainz_release_id: Optional[str] = None
    musicbrainz_recording_id: Optional[str] = None
    acoustid_id: Optional[str] = None
    acoustid_fingerprint: Optional[str] = None

    # Musical
    bpm: Optional[float] = None
    key_name: Optional[str] = None
    key_enum: Optional[KeyEnum] = None
    mode_enum: Optional[ModeEnum] = None
    energy: Optional[float] = None
    danceability: Optional[float] = None
    valence: Optional[float] = None

    # Audio técnico
    replay_gain: Optional[ReplayGain] = None
    artwork: Optional[ArtworkInfo] = None
    chapters: Optional[list] = None

    # Raw tags (tudo que mutagen encontrou)
    raw_tags: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        if self.key_name and self.mode_enum:
            return f"{self.key_name} {self.mode_enum.value}"
        return ""

    @property
    def format_label(self) -> str:
        if self.codec == AudioCodec.MP3 and self.bitrate_kbps:
            return f"MP3 {self.bitrate_kbps}kbps"
        elif self.codec == AudioCodec.FLAC:
            return f"FLAC {self.bit_depth}bit/{self.sample_rate_hz}Hz"
        else:
            return self.codec.value.upper()

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "codec": self.codec.value,
            "duration_ms": self.duration_ms,
            "bitrate_kbps": self.bitrate_kbps,
            "sample_rate_hz": self.sample_rate_hz,
            "channels": self.channels,
            "bit_depth": self.bit_depth,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "isrc": self.isrc,
            "musicbrainz_track_id": self.musicbrainz_track_id,
            "bpm": self.bpm,
            "key": self.key,
            "energy": self.energy,
            "format_label": self.format_label,
        }


class AudioExtractionService:
    """
    Extrai todos os metadados de arquivos de áudio usando mutagen.
    Stateless, thread-safe.
    """

    def __init__(self, enable_cache: bool = True, max_cache_size: int = 1000):
        self.enable_cache = enable_cache
        self.max_cache_size = max_cache_size
        if enable_cache:
            self._cached_extract: Callable[[str], AudioMetadata] = lru_cache(maxsize=max_cache_size)(self._do_extract)
        else:
            self._cached_extract = self._do_extract

    def extract(self, path: str) -> AudioMetadata:
        """Extrai metadados de um arquivo de áudio."""
        return self._cached_extract(path)

    def _do_extract(self, path: str) -> AudioMetadata:
        """Actual extraction implementation."""
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        codec = self._detect_codec(path_obj)
        audio = None
        try:
            audio = MutagenFile(path, easy=True)
        except Exception:
            try:
                audio = MutagenFile(path, easy=False)
            except Exception:
                pass

        if audio is None:
            return AudioMetadata(
                path=str(path_obj.resolve()),
                codec=codec,
                duration_ms=0,
            )

        length_ms = int(getattr(getattr(audio, "info", None), "length", 0) * 1000)

        # Raw tags
        raw_tags = {}
        if hasattr(audio, "tags") and audio.tags:
            for k, v in audio.tags.items():
                raw_tags[k] = v

        # Common tags
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
            if info:
                bitrate = info.bitrate // 1000 if info.bitrate else None
                sample_rate = info.sample_rate
                channels = info.channels
            try:
                id3 = ID3(path)
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
            except Exception:
                pass

        # FLAC specific
        elif codec == AudioCodec.FLAC and isinstance(audio, FLAC):
            if audio.info:
                sample_rate = audio.info.sample_rate
                channels = audio.info.channels
                bit_depth = audio.info.bits_per_sample
            if audio.tags:
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
            if audio.info:
                sample_rate = audio.info.sample_rate
                channels = audio.info.channels
            if audio.tags:
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

        # Get artwork from mutagen's pictures
        artwork = self._extract_artwork(audio)

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
        key_name, key_enum, mode_enum = self._extract_key_and_mode(raw_tags)
        if not key_name:
            # Try from common tag positions
            for tag in ["TMKEY", "key", " Musical Key", "TKEY"]:
                val = raw_tags.get(tag)
                if val:
                    key_name, key_enum, mode_enum = self._extract_key_and_mode({tag: val})
                    break

        return AudioMetadata(
            path=str(path_obj.resolve()),
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

    def _detect_codec(self, path: Path) -> AudioCodec:
        ext = path.suffix.lower()
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

    def _extract_artwork(self, audio) -> Optional[ArtworkInfo]:
        """Extrai artwork dos tags."""
        try:
            if hasattr(audio, "pictures") and audio.pictures:
                pic = audio.pictures[0]
                return ArtworkInfo(
                    mime_type=pic.mime or "image/jpeg",
                    width=pic.width,
                    height=pic.height,
                    depth=pic.depth,
                    size_bytes=len(pic.data),
                    data=pic.data,
                )
            elif hasattr(audio, "tags") and isinstance(audio.tags, ID3):
                for frame in audio.tags.values():
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
        except Exception:
            pass
        return None

    def _extract_key_and_mode(self, tags) -> tuple[Optional[str], Optional[KeyEnum], Optional[ModeEnum]]:
        """Tenta extrair key e mode de várias fontes."""
        key_str = None
        for key in ["TMKEY", "TCOMP", "key", " Musical Key"]:
            val = tags.get(key, [""])[0]
            if val:
                key_str = val.strip()
                break

        if not key_str:
            return None, None, None

        key_str = key_str.strip()
        major_indicators = ["", "M", " Maj", " Major"]
        minor_indicators = ["m", " m", " min", " Minor"]

        mode = ModeEnum.MAJOR
        for ind in minor_indicators:
            if key_str.endswith(ind):
                mode = ModeEnum.MINOR
                key_str = key_str[:-len(ind)]
                break

        key_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        for kn in key_names:
            if key_str == kn or key_str.lower() == kn.lower():
                return key_str, KeyEnum(kn), mode

        return key_str, None, mode

    def get_file_hash(self, path: str, algorithm: str = "sha256") -> str:
        """Calcula hash do arquivo."""
        h = hashlib.new(algorithm)
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
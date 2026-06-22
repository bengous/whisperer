# Whisperer

CLI locale et interface web optionnelle pour transcrire des fichiers audio ou
video avec [OpenAI Whisper](https://github.com/openai/whisper).

Whisperer est local-first: les medias restent sur la machine sauf si vous les
deplacez ailleurs. L'outil extrait l'audio des videos avec ffmpeg, convertit les
audios non compatibles en WAV mono 16 kHz, puis ecrit les sorties Whisper.

## Fonctionnalites

- Entrees audio et video: wav, mp3, flac, ogg, m4a, aac, wma, opus, mp4, mkv,
  avi, mov, webm, flv, wmv, m4v.
- Sorties: txt, srt, json, vtt, tsv, ou tous les formats.
- Choix du modele Whisper: tiny, base, small, medium, large, large-v2,
  large-v3, turbo.
- Indication optionnelle de langue, par exemple `fr` ou `en`.
- Interface web Flask locale avec upload de fichier et liens de telechargement.

## Non-fonctionnalites

- Pas de diarisation.
- Pas de durcissement pour hebergement distant ou authentification web.
- Pas de modele Whisper ni binaire ffmpeg embarque.
- Licence MIT.

## Installation

Prerequis:

- Python 3.14.6
- ffmpeg et ffprobe disponibles dans le `PATH`

Installation locale editable:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip==26.1.2
python -m pip install --require-hashes -r requirements.lock
python -m pip install -e . --no-deps --no-build-isolation
```

Sur Arch Linux, ffmpeg peut etre installe avec:

```bash
sudo pacman -S ffmpeg
```

## CLI

```bash
whisperer audio.wav
whisperer meeting.mp4 --model turbo --language fr --format srt
whisperer interview.mov --format all --output-dir results/
whisperer input.m4a --keep-intermediate
```

Equivalent sans installer les scripts console:

```bash
python -m whisperer meeting.mp4 --format vtt
```

Valeurs par defaut:

- modele: `turbo`
- format: `txt`
- dossier de sortie: `outputs/`
- langue: detection automatique

## Interface web

```bash
whisperer-web
# ou
python -m whisperer.web --port 5000
```

L'interface ecoute sur `127.0.0.1` par defaut. Traitez-la comme un outil local,
pas comme un service expose sur internet.

Le wrapper `./w` est conserve pour le developpement local. Il utilise
`.venv/bin/python` quand il existe, sinon `python`.

## Sorties

Les noms de sortie sont derives du nom d'entree original:

```text
meeting.mp4 -> outputs/meeting.srt
audio.wav   -> outputs/audio.txt
```

Avec `--format all`, Whisperer ecrit `txt`, `srt`, `json`, `vtt` et `tsv`.

Si un fichier du meme nom existe deja dans le dossier de sortie, le writer
Whisper le remplace. Utilisez `--output-dir` pour separer plusieurs executions.

Les medias locaux, sorties generees, caches, `.venv/` et artefacts agents
locaux (`.agents/`, `plans/`, `skills-lock.json`) sont ignores par git via
`.gitignore`.

## Depannage

- `Missing system dependency`: installez ffmpeg pour que `ffmpeg` et `ffprobe`
  soient disponibles dans le `PATH`.
- `Missing Python dependency`: lancez `python -m pip install -e .` dans
  l'environnement actif.
- Memoire CUDA insuffisante: essayez `--model turbo`, `--model medium` ou un
  modele plus petit, ou liberez de la memoire GPU.
- Les gros fichiers peuvent prendre longtemps et demander de l'espace disque
  pour la conversion WAV temporaire.

## Developpement

Validation rapide:

```bash
bash scripts/check.sh
```

La CI installe seulement le lock leger `requirements-ci.lock` pour garder le
check rapide. Le lock complet `requirements.lock` sert aux installations qui
doivent vraiment executer Whisper.

Les tests utilisent des fakes pour ffmpeg, ffprobe, Whisper et les writers. Ils
ne telechargent pas de modele et ne demandent pas de GPU.

Notes durables:

- Pipeline et boundaries: `docs/architecture.md`
- Checklist de publication future: `docs/release.md`
- Workflow agents: `AGENTS.md`

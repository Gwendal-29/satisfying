FROM python:3.12-slim

# cairo (dessin), polices, fuseaux horaires. ffmpeg est fourni par imageio-ffmpeg.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libcairo2 libcairo2-dev pkg-config gcc fonts-dejavu-core tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y libcairo2-dev pkg-config gcc && apt-get autoremove -y

COPY satisfy ./satisfy
COPY generate.py tiktok.py daily.py scheduler.py ./

ENV PYTHONUNBUFFERED=1 \
    DATA_DIR=/data \
    TZ=Europe/Paris
VOLUME /data

CMD ["python", "scheduler.py"]

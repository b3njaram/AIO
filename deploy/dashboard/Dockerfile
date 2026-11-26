FROM python:3.13-alpine@sha256:9ef1a599f863231c3d91e941389bfdc4a2d6070557243d54df1a4e57015b960e
RUN python -m pip uninstall -y setuptools wheel msgpack urllib3 pip && rm -rf /root/.cache/pip
WORKDIR /app
COPY --chmod=0644 server.py index.html home.svg manifest.webmanifest /app/
USER 65534:65534
EXPOSE 8080
CMD ["python","-B","/app/server.py"]
